from setuptools import setup, find_packages

setup(
    name='streamdeck-obs',
    version='1.0',
    packages=find_packages(),
    url='',
    license='',
    author='raoul',
    author_email='',
    description='',
    install_requires=[
        'setuptools',
        'simpleobsws',
        'Pillow',
        'streamdeck',
        'tkinter',
    ],
    scripts=["streamdeck.py"]
)
