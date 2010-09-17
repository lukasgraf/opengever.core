from setuptools import setup, find_packages
import os

version = '1.0a1-dev'
maintainer = 'Jonas Baumann'

setup(name='opengever.ogds.base',
      version=version,
      description="OpenGever directory service base package" + \
          ' (Maintainer: %s)' % maintainer,
      long_description=open("README.txt").read() + "\n" + \
          open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Framework :: Zope3",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='opengever ogds base',
      author='%s, 4teamwork GmbH',
      author_email='GPL2',
      url='http://psc.4teamwork.ch/4teamwork/kunden/' + \
          'opengever/opengever-ogds-base',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['opengever', 'opengever.ogds'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',
        'SQLAlchemy',
        # -*- Extra requirements: -*-
        ],
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
