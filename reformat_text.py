#!/usr/bin/env python3

# read lines from stdin and remove all occurances of \n followed by 5 spaces

import sys
input = []
with sys.stdin as f:
  input = ''.join(f.readlines())

# output = input.replace('\n     ', '')
# output = output.replace('\n ', '')
output = input

print(output)

