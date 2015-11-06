from setuptools import setup, find_packages

setup(
    name="CatalogClient",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "catalog-docker-agent = agents.docker_agent:main", # run on agent nodes only
            #"catalog-log-agent = agents.log_agent:main", # run on every node
            #"catalog-dataset-agent = agents.dataset_agent:main", # run on control service
        ],
    },
    version="0.1",
    description="Agents for sending data to the ClusterHQ SaaS Volume Catalog",
    author="ClusterHQ, Inc.",
    author_email="flocker-users@clusterhq.com",
    url="https://github.com/ClusterHQ/volume-catalog",
    install_requires=[
        "PyYAML>=3",
        "Twisted>=14",
        "treq>=14",
        "pyasn1>=0.1",
        "docker-py>=1.5.0",
        "pyrsistent>=0.11.9",
        "eliot>=0.9.0",
    ],
)
