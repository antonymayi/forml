"""Generic assets directory.
"""
import logging
import typing

from forml import error  # pylint: disable=unused-import; # noqa: F401
from forml.runtime.asset import directory
from forml.runtime.asset.directory import lineage as lngmod

if typing.TYPE_CHECKING:
    from forml.project import distribution
    from forml.runtime.asset.directory import root as rootmod

LOGGER = logging.getLogger(__name__)


# pylint: disable=unsubscriptable-object; https://github.com/PyCQA/pylint/issues/2822
class Level(directory.Level[str, lngmod.Version]):
    """Sequence of lineages based on same project.
    """
    def __init__(self, root: 'rootmod.Level', key: str):
        super().__init__(str(key), parent=root)

    def list(self) -> directory.Level.Listing[lngmod.Version]:
        """List the content of this level.

        Returns: Level content listing.
        """
        return self.Listing(lngmod.Version(l) for l in self.registry.lineages(self.key))

    def get(self, lineage: typing.Optional[lngmod.Version] = None) -> lngmod.Level:
        """Get a lineage instance by its id.

        Args:
            lineage: Lineage version.

        Returns: Lineage instance.
        """
        return lngmod.Level(self, lineage)

    def put(self, package: 'distribution.Package') -> lngmod.Level:
        """Publish new lineage to the repository based on provided package.

        Args:
            package: Distribution package to be persisted.

        Returns: new lineage instance based on the package.
        """
        project = package.manifest.name
        lineage = package.manifest.version
        try:
            previous = self.list().last
        except (directory.Level.Invalid, directory.Level.Listing.Empty):
            LOGGER.debug('No previous lineage for %s-%s', project, lineage)
        else:
            if project != self.key:
                raise error.Invalid(f'Project key mismatch')
            if not lineage > previous:
                raise directory.Level.Invalid(f'{project}-{lineage} not an increment from existing {previous}')
        self.registry.push(package)
        return self.get(lineage)
