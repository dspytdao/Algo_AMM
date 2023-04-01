"""pip package publishing"""
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="algo_amm",
    version="0.0.2",
    author="pfedprog",
    author_email="pfedprog@gmail.com",
    description="Automated Prediction Market Maker on Algorand",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dspytdao/Algo_AMM",
    packages=setuptools.find_packages(),
    install_requires=['pyteal', 'py-algorand-sdk'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
