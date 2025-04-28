from setuptools import setup, find_packages

setup(
    name='spectrometer',
    version='0.0.1',
    author='Vorobev Dmitri Alexandrovich',
    author_email='vorobev.da@phystech.edu',
    description='Spectrometer Application - Control of the spectrometer based on Raspberry Pi Camera.',
    long_description=open('../README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Dvorobev-MIPT/Spectrometer/blob/main/UI.py',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
    ],
    python_requires='>=3.6',
    install_requires=[
        'PyQt5',
        'numpy',
        'picamera2'
    ],
    entry_points={
        'console_scripts': [
            'spectrometer=Spectrometer.ui.main_window:main',
        ],
    },
)