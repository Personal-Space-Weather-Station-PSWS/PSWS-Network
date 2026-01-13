// stationcreation.c - adds a userID plus password into stations group for new PSWS station creation
// Authors: Cole Robbins, Nicholas Muscolino, University of Alabama,  May, 2022
// Modifications by W. Engelke, July 2022
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
	//Ensure we are running as root
	setuid(0);

	//Should always be run as ./stationcreation username password
	//Usrename should follow the U000000 format
	//Password must be 32 characters
	if(argc != 3) {
		printf("Incorrect usage");
		exit(1);
	}

	//Commmand 1 will be useradd
	char command1[20];
	//Command 2 will be setting the password which must be done via echo
	char command2[75];

	char useradd[10], echo[10], passwd[20];
        char usergroup[14];

	//These do not use user input so safe to use strcpy
	strcpy(useradd, "useradd ");
        strcpy(usergroup, " -g stations ");
	strcpy(echo, "echo -n ");
	strcpy(passwd, " | passwd --stdin ");

	//Using strncat from this point forward since it is safer to buffer overflow
	strcpy(command1, useradd);
	strncat(command1, argv[1], 8);
        strncat(command1, usergroup, 14);

	strcpy(command2, echo);
	strncat(command2, argv[2], 32);
	strncat(command2, passwd, 19);
	strncat(command2, argv[1], 8);

	command1[28] = '\0';
	command2[65] = '\0';
	
//    printf("%s", command1);
//    printf ("%s", "\n");
//    printf("%s", command2);
//    printf("%s", "\n");
	system(command1);
	system(command2);

	//Next command is to make the user's default group the stations group
// removed, WDE
//	char command3[28];
//	char usermod[21];
//	strcpy(usermod, "usermod -g stations ");
//	strcpy(command3, usermod);
//	strncat(command3, argv[1], 8);
//	system(command3);

	//Last command is to add group execute access to the user's home directory 
	char command4[24];
	char chmod[19];
	strcpy(chmod, "chmod go+rx /home/");  // orig was chmmod g+x /home/
	strcpy(command4, chmod);
	strncat(command4, argv[1], 8);
	system(command4);

	exit(0);
}
