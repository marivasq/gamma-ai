#!/bin/bash

# Setup nothing on savio
if [[ ${HOSTNAME} == *.brc ]]; then
  exit
fi

# If this is Linux and MEGAlib is not installed, install MEGAlib
if [ "$(uname -s)" != "Darwin" ]; then
  if [[ ! -f ${MEGALIB}/bin/cosima ]]; then
    HERE=$(pwd)
    cd ..
    git clone https://github.com/zoglauer/megalib.git MEGAlib
    cd MEGAlib
    bash setup.sh --branch=master --clean=yes

    HEADER="# MEGAlib options  --  do not modify"
    FOOTER="# MEGAlib end"

    CONFIG="source $(pwd)/bin/source-megalib.sh"

    if [[ -f ~/.bashrc ]]; then 
      HASSTART=$(grep "${HEADER}" ~/.bashrc)
      HASEND=$(grep "${FOOTER}" ~/.bashrc)

      cp ~/.bashrc ~/.bashrc.backup$(date +%Y%m%d%H%M%S)

      if [[ ${HASSTART} != "" ]] && [[ ${HASEND} != "" ]]; then
        # Delete the old
        sed -i "/${HEADER}/,/${FOOTER}/d" ~/.bashrc 
        HASSTART=""
        HASEND=""
      fi

      if [[ ${HASSTART} == "" ]] && [[ ${HASEND} == "" ]]; then
        echo "${HEADER}" >> ~/.bashrc
        echo "${CONFIG}" >> ~/.bashrc
        echo "${FOOTER}" >> ~/.bashrc
      else
        echo "ERROR: Broken configuration in .bashrc"
        exit
      fi
    else
      echo "ERROR: No .bashrc found"
    fi
    
    . $(pwd)/bin/source-megalib.sh

    cd ${HERE}
  fi
fi



PENV=python-env

if [[ ${HOSTNAME} == thebe ]]; then
  export TMPDIR=/volumes/selene/tmp
fi

if [ -d ${PENV} ]; then
  rm -r ./${PENV}
fi
python3 -m venv ${PENV}
. ${PENV}/bin/activate
pip3 install -r Requirements.txt

if [[ ${HOSTNAME} == thebe ]] || [[ ${HOSTNAME} == despina ]]; then
  pip install tensorflow-gpu==2.3
fi


