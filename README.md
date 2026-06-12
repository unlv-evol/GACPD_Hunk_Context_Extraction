A program that extracts info from the output of GACPD.
The extractions include:
1. A summary of the results of GACPD including hunk similarity data.
2. The AST representation of the context of every qualified hunk
3. The source code of the context of every qualified hunk

Number 2 and 3 will be done for each qualified hunk, and will be stored
hierarchically in an output folder determined by the user.


IMPORTANT:
To use the program, create Config.py in the main folder, and copy the content of 
Config_Template.txt to it. Then you can edit the directories and controls as you wish
to customize the program to your liking.
