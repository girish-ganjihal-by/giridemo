import os
from typing import List

from setuptools import find_packages, setup

current_dir = os.path.dirname(os.path.realpath(__file__))


def get_install_requirements(path: str) -> List[str]:
    content = open(os.path.join(current_dir, path)).read()
    requirements = [
        req for req in content.split("\n") if req != "" and not req.startswith("#")
    ]
    return requirements


def setup_package() -> None:
    setup(
        name="pycatmanadapter",
        author="Blue Yonder",
        setup_requires=["setuptools", "setuptools-scm"],
        install_requires=get_install_requirements("requirements.in"),
        tests_require=get_install_requirements("test-requirements.in"),
        packages=find_packages(exclude=["tests"]),
        use_scm_version=True,
        long_description=open("README.md", "r").read(),
        long_description_content_type="text/markdown",
        python_requires=">=3.8",
    )


if __name__ == "__main__":
    setup_package()
