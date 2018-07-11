pipeline {
  agent {
    node {
      label 'Node Label'
    }

  }
  stages {
    stage('Run Buildout') {
      steps {
        sh 'ln -s test-plone-4.3.x.cfg buildout.cfg && python2.7 bootstrap.py && bin/buildout'
      }
    }
    stage('Run tests') {
      steps {
        sh 'bin/test-jenkins'
      }
    }
  }
}