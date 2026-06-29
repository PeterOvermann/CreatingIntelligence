// -------------------------------------------------------------------------- //
//	testing.c
//	Performance and capacity tests of the memory algorithm
// 	https://creatingintelligence.org
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
//	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIN.D,
//	EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
//	MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
// -------------------------------------------------------------------------- //


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include <time.h>

#include "memory.h"

// -------------------------------------------------------------------------- //
//	 Test Configuration
// -------------------------------------------------------------------------- //

#define	UNKNOWN		0		// 0: Test against training data
							// 1: Test against unknown inputs

#define NOISE 		0		// Random elements added/removed (can be negative)
				
#define ITEMS		50000	// Items per iteration
#define ITERATIONS	40		// Number of iterations
#define PREFILL		0		// Items to write before testing

#define Adim		1000	// Hyperparameters
#define Apop		10
#define Bdim		1001	// Auto-associative if Adim == Bdim
#define Bpop		10


#define OPS ((int)round((double)ITEMS*CLOCKS_PER_SEC/((double)(clock()-start))))

int main(int argc, char *argv[])
	{
 	clock_t start;
 	int autoassociative = Adim == Bdim, unknowninputs = UNKNOWN;
 	
	if (autoassociative)
		printf("\n\nAuto-associative memory A->A at %d/%d, ", Adim, Apop);
	else
		printf("\n\nHetero-associative memory A->B at %d/%d and %d/%d, ", Adim, Apop, Bdim, Bpop);

	if (unknowninputs)	printf("\n   testing against unknown inputs with %d elements\n", Apop);
	else 				printf("noise = %d\n", NOISE);

	if (unknowninputs)
		printf("\n| %10s | %10s | %10s | %10s | %10s | %10s |\n|",
			"items","writes/s","memory","reads/s","false pos","overlap");
	else
		printf("\n| %10s | %10s | %10s | %10s | %10s | %10s |\n|",
			"items","writes/s","memory","reads/s","distance","overlap");
				
	for (int i = 0; i < 6; i++) printf("------------|"); printf("\n");
		
	Memory *M = Memory_new(Adim, Apop, Bdim, Bpop);
	
	Set **x = malloc(ITEMS * sizeof(Set*)),
		**y = malloc(ITEMS * sizeof(Set*)),
		**Y = malloc(ITEMS * sizeof(Set*));

	for (int i = 0; i < ITEMS; i++)
		{
		x[i] = Set_new(Adim); y[i] = Set_new(Bdim);
		Y[i] = Set_new(Bdim);
		}
						
	for (int i = 0; i < PREFILL; i++)
		{ // repurpose x[0] and y[0] instead of allocating new sets
		Set_random(x[0], Apop); Set_random(y[0], Bpop);
		if (autoassociative) Set_copy(y[0], x[0]);
		Memory_write(M, x[0], y[0]);
		}
				
	for (int iter = 1; iter <= ITERATIONS; iter ++)
		{
		// Generate test data
		for (int i = 0; i < ITEMS; i++)
			{
			Set_random(x[i], Apop); Set_random(y[i], Bpop);
			if (autoassociative) Set_copy(y[i], x[i]);
			}
		printf("| %10d |", iter * ITEMS + PREFILL); fflush(stdout);

		// Write test data
		start = clock();
		for (int i = 0; i < ITEMS; i++) Memory_write(M, x[i], y[i]);
		printf(" %10d |", OPS); fflush(stdout);
		printf(" %10.6f |",((double)Memory_count(M)) / (double)Bdim / (double)(Adim*(Adim-1)/2)); fflush(stdout);

		// Read test data
		start = clock();
		for (int i = 0; i < ITEMS; i++)
			if (unknowninputs)	Memory_read (M, Set_random(x[i], Apop), Y[i]);
			else				Memory_read (M, Set_noise(x[i], NOISE), Y[i]);

		printf(" %10d |", OPS); fflush(stdout);
		
		int H = 0, OV = 0;// Accumulated distance and overlap scores.
		for (int i = 0; i < ITEMS; i++)
			{
			if (unknowninputs) 	H += (Y[i]->p > 0); // Count non-zero responses
			else				H += distance(y[i], Y[i]);
			OV += overlap (y[i], Y[i]);
			}
		printf(" %10.6f | %10.6f |\n", ((double)H)/ITEMS, ((double)OV)/ITEMS);
		}
	Memory_free(M);
	return 0;
	}
