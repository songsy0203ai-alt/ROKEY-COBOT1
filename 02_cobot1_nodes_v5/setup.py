from setuptools import setup
import os
from glob import glob

package_name = 'cobot1_nodes_v5'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    package_dir={'': '.'},
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ssy',
    maintainer_email='ssy@todo.todo',
    description='Robot control and Firebase bridge nodes',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'integration_node_v5 = cobot1_nodes_v5.integration_node_v5:main',
            'control_node_v5 = cobot1_nodes_v5.control_node_v5:main',
            'db_bridge_node_v5 = cobot1_nodes_v5.db_bridge_node_v5:main',
        ],
    },
)