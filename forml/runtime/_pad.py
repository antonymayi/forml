# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Launch support components.
"""
import functools
import logging
import typing

from forml import io
from forml import project as prj
from forml import provider as provmod
from forml import setup
from forml.io import asset, dsl

from . import _agent, _service

LOGGER = logging.getLogger(__name__)

Provider = typing.TypeVar('Provider', bound=provmod.Service)


def ensure_instance(
    config_or_instance: typing.Union[setup.Provider, provmod.Service],
    provider: type[Provider],
    *args,
    **kwargs,
) -> Provider:
    """Helper for returning a provider instance.

    Args:
        config_or_instance: Provider config or existing instance.
        provider: Provider type.

    Returns:
        Provider instance.
    """
    if isinstance(config_or_instance, setup.Provider):
        config_or_instance = provider[config_or_instance.reference](*args, **(config_or_instance.params | kwargs))
    return config_or_instance


class Repo:
    """Registry util handle."""

    def __init__(self, registry: typing.Union[setup.Registry, asset.Registry]):
        self._asset: asset.Directory = asset.Directory(ensure_instance(registry, asset.Registry))

    def assets(
        self, project: typing.Optional[str], release: typing.Optional[str], generation: typing.Optional[str]
    ) -> asset.Instance:
        """Create the assets instance of given registry item.

        Args:
            project: Item's project.
            release: Item's release.
            generation: Item's generation.

        Returns:
            Asset instance.
        """
        return asset.Instance(project, release, generation, self._asset)

    def publish(self, project: str, package: prj.Package) -> None:
        """Publish new package into the registry.

        Args:
            project: Name of project to publish the package into.
            package: Package to be published.
        """
        self._asset.get(project).put(package)

    def list(self, project: typing.Optional[str], release: typing.Optional[str]) -> typing.Iterable[asset.Level.Key]:
        """Repository listing subcommand.

        Args:
            project: Name of project to be listed.
            release: Release version to be listed.

        Returns:
            Listing of the given registry level.
        """
        level = self._asset
        if project:
            level = level.get(project)
            if release:
                level = level.get(release)
        return level.list()


class Launcher:
    """Runner handle."""

    def __init__(self, runner: setup.Runner, assets: asset.Instance, feeds: io.Importer, sink: io.Exporter):
        self._runner: setup.Runner = runner
        self._assets: asset.Instance = assets
        self._feeds: io.Importer = feeds
        self._sink: io.Exporter = sink

    @property
    def train_call(self) -> typing.Callable[[typing.Optional[dsl.Native], typing.Optional[dsl.Native]], None]:
        """Return the train handler.

        Returns:
            Train runner.
        """
        return self(self._assets.project.source.extract.train).train

    @property
    def train_return(self) -> typing.Callable[[typing.Optional[dsl.Native], typing.Optional[dsl.Native]], None]:
        """Return the train handler.

        Returns:
            Train runner.
        """
        return self(self._assets.project.source.extract.train, self._sink.apply).train

    @property
    def apply(self) -> typing.Callable[[typing.Optional[dsl.Native], typing.Optional[dsl.Native]], None]:
        """Return the apply handler.

        Returns:
            Apply handler.
        """
        return self(self._assets.project.source.extract.apply, self._sink.apply).apply

    @property
    def eval_traintest(self) -> typing.Callable[[typing.Optional[dsl.Native], typing.Optional[dsl.Native]], None]:
        """Return the eval handler.

        Returns:
            Eval runner.
        """
        return self(self._assets.project.source.extract.train, self._sink.eval).eval_traintest

    @property
    def eval_perftrack(self) -> typing.Callable[[typing.Optional[dsl.Native], typing.Optional[dsl.Native]], None]:
        """Return the eval handler.

        Returns:
            Eval runner.
        """
        return self(self._assets.project.source.extract.train, self._sink.eval).eval_perftrack

    @property
    def tune(self) -> typing.Callable[[typing.Optional[dsl.Native], typing.Optional[dsl.Native]], None]:
        """Return the tune handler.

        Returns:
            Tune handler.
        """
        raise NotImplementedError()

    def __call__(self, statement: dsl.Statement, sink: typing.Optional[io.Sink] = None) -> _agent.Runner:
        return ensure_instance(self._runner, _agent.Runner, self._assets, self._feeds.match(statement), sink)


class Service:
    """Helper class for wrapping all requirements for a gateway service."""

    def __init__(
        self,
        gateway: setup.Gateway,
        inventory: typing.Union[setup.Inventory, asset.Inventory],
        registry: typing.Union[setup.Registry, asset.Registry],
        feeds: io.Importer,
    ):
        inventory: asset.Inventory = ensure_instance(inventory, asset.Inventory)
        registry: asset.Registry = ensure_instance(registry, asset.Registry)
        self._gateway: _service.Gateway = ensure_instance(gateway, _service.Gateway, inventory, registry, feeds)

    def run(self) -> None:
        """Launch the gateway service."""
        self._gateway.main()


class Platform:
    """Handle to the runtime functions representing a ForML platform."""

    def __init__(
        self,
        runner: typing.Optional[typing.Union[setup.Runner, str]] = None,
        registry: typing.Optional[typing.Union[setup.Registry, asset.Registry]] = None,
        feeds: typing.Optional[typing.Iterable[typing.Union[setup.Feed, str, io.Feed]]] = None,
        sink: typing.Optional[typing.Union[setup.Sink.Mode, str, io.Sink]] = None,
        inventory: typing.Optional[typing.Union[setup.Inventory, asset.Inventory]] = None,
        gateway: typing.Optional[setup.Gateway] = None,
    ):
        if isinstance(runner, str):
            runner = setup.Runner.resolve(runner)
        self._runner: setup.Runner = runner or setup.Runner.default
        self._registry: typing.Union[setup.Registry, asset.Registry] = registry or setup.Registry.default
        self._feeds: io.Importer = io.Importer(*(feeds or setup.Feed.default))
        self._sink: io.Exporter = io.Exporter(sink or setup.Sink.Mode.default)
        self._inventory: typing.Union[setup.Inventory, asset.Inventory] = inventory or setup.Inventory.default
        self._gateway: setup.Gateway = gateway or setup.Gateway.default

    def launcher(
        self,
        project: typing.Optional[str],
        release: typing.Optional[str] = None,
        generation: typing.Optional[str] = None,
    ) -> Launcher:
        """Get a runner handle for given project/release/generation.

        Args:
            project: Project to run.
            release: Release to run.
            generation: Generation to run.

        Returns:
            Runner handle.
        """
        return Launcher(self._runner, self.registry.assets(project, release, generation), self._feeds, self._sink)

    @property
    def service(self) -> Service:
        """Service handle getter.

        Returns:
            Service handle.
        """
        return Service(self._gateway, self._inventory, self._registry, self._feeds)

    @functools.cached_property
    def registry(self) -> Repo:
        """Registry handle getter.

        Returns:
            Registry handle.
        """
        return Repo(self._registry)
