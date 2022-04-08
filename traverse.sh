#!/bin/bash

function read_dir(){
		for file in `ls -a $1`
		do
				if [ -d $1'/'$file ];then
						if [[ $file != '.' && $file != '..' ]];then
								read_dir $1'/'$file
						fi
				else
						if [[ $file =~ \color.zip$ ]];then
								unzip -n -d $1'/color' $1'/'$file
						elif [[ $file =~ \groundtruth.zip$ ]];then
								unzip -o -d $1 $1'/'$file
						fi
				fi
		done
}

read_dir `pwd`
