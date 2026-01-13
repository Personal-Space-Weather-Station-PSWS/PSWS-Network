#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
	//Ensure we are running as root
	setuid(0);

	//SHould always be ran as ./stationcreation username password
	//Usrename should follow the N000000 format
	//Password must be 32 characters
	if(argc != 3) {
		printf("Incorrect usage");
		exit(1);
	}

	//COmmand 1 will be useradd
	char command1[20];
	//Command 2 will be setting the password which must be done via echo
	char command2[75];

	char useradd[10], echo[10], passwd[20];

	//These do not use user input so safe to use strcpy
	strcpy(useradd, "useradd ");
	strcpy(echo, "echo -n ");
	strcpy(passwd, " | passwd --stdin ");

	//Using strncat from this point forward since it is safer to buffer overflow
	strcpy(command1, useradd);
	strncat(command1, argv[1], 8);

	strcpy(command2, echo);
	strncat(command2, argv[2], 32);
	strncat(command2, passwd, 19);
	strncat(command2, argv[1], 8);

	command1[15] = '\0';
	command2[65] = '\0';
	
	system(command1);
	system(command2);

	//Next command is to make the user's default group the stations group
	char command3[28];
	char usermod[21];
	strcpy(usermod, "usermod -g stations ");
	strcpy(command3, usermod);
	strncat(command3, argv[1], 8);
	system(command3);

	//Last command is to add group execute access to the user's home directory 
	char command4[24];
	char chmod[17];
	strcpy(chmod, "chmod g+x /home/");
	strcpy(command4, chmod);
	strncat(command4, argv[1], 8);
	system(command4);

	exit(0);
}
