// -------------------------------------------------------------------------- //
//	commandline.c
//	commandline wrapper for the core memory algorithm. 
//	https://creatingintelligence.org
// -------------------------------------------------------------------------- //
//
//	Copyright (c) 2026 Peter Overmann
//
//	SPDX-License-Identifier: MIT
//
//	This file is part of the "Creating Intelligence" C reference library.
//	It is licensed under the MIT License. You may obtain a copy of the 
//	License in the LICENSE file in the root directory of this repository.
//
//	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
//	EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
//	MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
// -------------------------------------------------------------------------- //


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "memory.h"


static void print_help(void)
	{
	printf("Associative Memory\n");
	
	printf("Command line arguments: dimensions n and populations p\n");
	printf("memory <na> <pa> <na> <pa>\n\n");

	printf("Command line pption: \n");
	printf("   -T <threshold>\n\n");

	printf("Store A -> B:\n");
	printf("1 2 3 4 5 6 7 8 9 10 -> 11 12 13 14 15 16 17 18 19 20\n\n");

	printf("Retrieve B from input A:\n");
	printf("1 2 3 4 5 6 7 8 9 10\n\n");

	printf("Memory count in bits\n");
	printf("   mem\n\n");

	printf("End process\n");
	printf("   quit\n");
	}
	
	
static char* Set_parse (char *buf, Set *s)
	{
	s->p = 0;
	
	while ( *buf  && *buf != ',' )
		{
		while (isspace(*buf)) buf++;
		if (! isdigit(*buf)) break;
		
		int *i = s->a + s->p;
		sscanf( buf, "%d", i);
		
		if ( (*i)-- < 0 ) // subtracting 1 to convert to C convention
			{
			printf("Set index must be greater than zero: %s\n", buf);
			exit(2);
			}
		s->p ++;
		
		while (isdigit(*buf)) buf++;
		while (isspace(*buf)) buf++;
		}
		
	return buf;
	}


int main(int argc, char *argv[])
	{
	char *buf, inputline[10000];
	
	int nx, px, ny, py;

	int arguments = argc, a = 0;
	
	// User-defined activation threshold
	int pmin = 0;
	if (arguments == 7 && strcmp(argv[1], "-T") == 0)
		{
		++a; sscanf( argv[++a], "%d", &pmin);
		arguments = arguments - 2;
		}

	if (arguments != 5 )
		{ print_help(); exit(1); }
		
	sscanf( argv[++a], "%d", &nx);
	sscanf( argv[++a], "%d", &px);

	sscanf( argv[++a], "%d", &ny);
	sscanf( argv[++a], "%d", &py);
	  
	Set 	*x	= Set_new(nx),
   			*y	= Set_new(ny);
    	
	Memory *H 	= Memory_new(nx, px, ny, py);
	
	if (pmin > 0) Memory_set_threshold (H, pmin);
	
	while (	fgets(inputline, sizeof(inputline), stdin) != NULL)
		{
		if ( strcmp(inputline, "mem\n") == 0)
			{ printf("%lld\n", Memory_count(H)); fflush(stdout);}
				
		else if ( strcmp(inputline, "quit\n") == 0)
			return 0;

		else // parse x
			{
			buf = inputline;
			buf = Set_parse(buf, x);
			
			// Read x, return x -> y (or an empty line if no match was found.
			if (*buf == 0)
				{
				Memory_read(H, x, y);
				if (y->p)
					Set_print(y, 1);
				printf("\n"); fflush(stdout);
				}
			
			// Write x -> y.
			else if (*buf == '-' && *(buf+1) == '>')
				{
				buf = Set_parse(buf+2, y);
				Memory_write(H, x, y);
				}
					
			else	{
				printf("invalid input\n");
				exit(5);
				}
			}
		}
	
	return 0;
	}



// end of file
