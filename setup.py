from setuptools import setup, find_packages

setup(
    name="gaaags-mvp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-generativeai>=0.3.0",
        "Pillow>=10.0.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.8",
) 