pipeline {
  agent any
  stages {
    stage('Run Buildout') {
      steps {
        sh 'ln -s test-plone-4.3.x.cfg buildout.cfg && python bootstrap.py && bin/buildout -v'
      }
    }
    stage('Run tests') {
      steps {
        sh 'bin/test-jenkins'
      }
    }
  }
}