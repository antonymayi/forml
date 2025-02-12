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
Titanic project.
"""
import pathlib

import setuptools

from forml import project

setuptools.setup(
    name='forml-tutorial-titanic',
    version='0.1.dev1',
    packages=setuptools.find_packages(include=['titanic*'], where=pathlib.Path(__file__).parent),
    setup_requires=['forml'],
    install_requires=['openschema', 'scikit-learn', 'pandas', 'numpy'],
    distclass=project.Distribution,
)
