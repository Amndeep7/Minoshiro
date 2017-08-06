from setuptools import setup

with open('README.md') as f:
    readme = f.read()

with open('requirements.txt') as r:
    requirements = r.read().splitlines()

extras_require = {
    'postgres': ['asyncpg>=0.12.0']
}

setup(
    name='roboragi',
    version='0.1.0',
    description=('An async Python3.6 library to search for anime, manga and'
                 'light novel using various web apis.'),
    long_description=readme,
    url='https://github.com/MaT1g3R/Roboragi',
    author='MaT1g3R, dashwav, Nihilate',
    license='MIT',
    packages=['roboragi'],
    include_package_data=True,
    install_requires=requirements,
    extras_require=extras_require,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English'
    ]
)
