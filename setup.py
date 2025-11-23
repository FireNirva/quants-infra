from setuptools import setup, find_packages

setup(
    name='quants-infrastructure',
    version='0.2.0',
    description='Unified infrastructure management for quantitative trading systems',
    author='Jonathan.Z',
    packages=find_packages(),
    install_requires=[
        'click>=8.0',
        'ansible-runner>=2.3',
        'docker>=6.0',
        'boto3>=1.26',
        'paramiko>=3.0',
        'jinja2>=3.1',
        'pyyaml>=6.0',
        'tabulate>=0.9',
        'colorama>=0.4',
        'python-dotenv>=1.0',
    ],
    entry_points={
        'console_scripts': [
            'quants-ctl=cli.main:cli',
        ],
    },
    python_requires='>=3.10',
)

