from setuptools import setup, find_packages

requirements = [
    'alpaca-py==0.24.0',
    'annotated-types==0.7.0',
    'appnope==0.1.4',
    'asttokens==2.4.1',
    'certifi==2024.6.2',
    'charset-normalizer==3.3.2',
    'comm==0.2.2',
    'debugpy==1.8.2',
    'decorator==5.1.1',
    'executing==2.0.1',
    'idna==3.7',
    'ipykernel==6.29.4',
    'ipython==8.25.0',
    'jedi==0.19.1',
    'jupyter_client==8.6.2',
    'jupyter_core==5.7.2',
    'matplotlib-inline==0.1.7',
    'msgpack==1.0.8',
    'nest-asyncio==1.6.0',
    'numpy==2.0.0',
    'packaging==24.1',
    'pandas==2.2.2',
    'parso==0.8.4',
    'pexpect==4.9.0',
    'platformdirs==4.2.2',
    'prompt_toolkit==3.0.47',
    'psutil==6.0.0',
    'ptyprocess==0.7.0',
    'pure-eval==0.2.2',
    'pydantic==2.7.4',
    'pydantic_core==2.18.4',
    'Pygments==2.18.0',
    'python-dateutil==2.9.0.post0',
    'pytz==2024.1',
    'pyzmq==26.0.3',
    'requests==2.32.3',
    'setuptools==70.1.1',
    'six==1.16.0',
    'sseclient-py==1.8.0',
    'stack-data==0.6.3',
    'tornado==6.4.1',
    'traitlets==5.14.3',
    'typing_extensions==4.12.2',
    'tzdata==2024.1',
    'urllib3==2.2.2',
    'wcwidth==0.2.13',
    'websockets==12.0'
]

setup(
    name='tradeAPP4',
    version='0.4',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'trade_app4=tradeAPP.main:main',
        ],
    },
)
