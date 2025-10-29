from setuptools import setup, find_packages

setup(
    name="figma-to-digitalocean",
    version="1.0.0",
    description="Extract images from Figma and upload to DigitalOcean Spaces",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "boto3>=1.34.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'figma-to-do=main:main',
        ],
    },
)