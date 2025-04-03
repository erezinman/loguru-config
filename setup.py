from setuptools import setup, find_namespace_packages

setup(
    name='loguru-config',
    version='0.1.0',
    author='Erez Zinman',
    description='Loguru configuration from configuration files.',
    license='MIT',
    url='https://github.com/erezinman/loguru-config',
    long_description=open('README.md').read(),
    packages=find_namespace_packages(include=['loguru_config*']),
    python_requires='>=3.7',
    keywords=['loguru', 'configuration', 'config', 'logging', 'log'],
    install_requires=[
        'loguru>=0.7.0'
    ],
    extras_require={
        "json5": ["pyjson5"],
        "yaml": ["PyYAML"],
        "toml": ["tomli"],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Logging',
    ]
)
