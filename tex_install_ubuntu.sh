#!/bin/bash

to_install=""
for expkg in texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-fonts-extra biber ghostscript
do
	if dpkg -l | grep -q ${expkg}; then
		echo "${expkg} is already installed"
		continue
	fi
	to_install="${to_install} ${expkg}"
done
if [ ! -z ${to_install} ]; then
	sed -i 's|http://deb.debian.org/debian-security|http://deb.debian.org/debian|g' /etc/apt/sources.list
	apt-get update
	apt-get install ${to_install} -y --fix-missing
fi
