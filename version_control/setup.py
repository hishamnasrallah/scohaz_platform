from setuptools import setup, find_packages

setup(
    name='django-version-control',
    version='0.1.0',
    description='A Django-based version control system with full snapshots and diffs, including safe soft deletion and restoration.',
    author='Hisham Nasrallah',
    author_email='hisham.nasralla@gmail.com',
    url='https://github.com/yourusername/django-version-control',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django>=3.11',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Programming Language :: Python',
    ],
)
