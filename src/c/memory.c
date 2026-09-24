// -------------------------------------------------------------------------- //
//	memory.c
//	Standard C, zero-dependency library.
//	Implements the core memory algorithm.
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
#include <time.h>
#include <math.h>

// Define M_LN2 if the compiler environment doesn't provide it
#ifndef M_LN2
#define M_LN2 0.6931471805599453094172321
#endif


#include "memory.h"

// -------------------------------------------------------------------------- //
//	 Set - data structure and utilities
// -------------------------------------------------------------------------- //


// 	Initialize random generator with current time
// 	All procedures that use rand() should call this

static void srand_init(void)
	{
	static int initialized = 0;
	if (! initialized)
		{
		srand((unsigned int)time(NULL));
		initialized = 1;
		}
	}

static inline int ucmpfunc (const void * a, const void * b)
	{
    unsigned int arg1 = *(const unsigned int*)a;
    unsigned int arg2 = *(const unsigned int*)b;
    if (arg1 < arg2) return -1;
    if (arg1 > arg2) return 1;
    return 0;
	}
	
Set* Set_random( Set*A, int p) // fill s with p random bits (in place)
	{
	srand_init();
	
	int n = A->n;
	A->p = p;

	int* range = (int*)malloc(n * sizeof(int));

	for (int i = 0; i < n; i++) range[i] = i; // initialize with integers 0 to n-1
	
	for (int k = 0; k < p; k++) // random selection of p integers in the range 0 to n-1
		{
		int r = rand() % n;
		A->a[k] = range[r];
		int tmp = range[n-1]; range[n-1] = range[r]; range[r] = tmp; // swap selected value to the end
		n--; // values swapped to the end won't get picked again
		}
	
	qsort( A->a, p, sizeof(int), ucmpfunc);

	free(range);

	return A;
	}
	

// 	Add noise to a Set, operating in place
// 		elements > 0 : add random elements
// 		elements < 0 : remove random elements
	
Set* Set_noise( Set*A, int elements)
	{
	if (elements == 0) return A;
	
	Set* t = Set_new_copy(A); 
	
	if (elements >= 0) // add elements (salt noise)
		{
		// Add random Set r
		// If r and A overlap, less than 'elements' elements will be added
		
		Set* r = Set_new(A->n);
		Set_union(A, t, Set_random(r, elements));
		Set_free(r);
		}
		
	else	{
		// remove elements (pepper noise)
		srand_init();

		A->p += elements;
		if (A->p < 0) A->p = 0;
		
		for (int k = 0; k < A->p; k++) // random selection of s->p integers from Set t
			{
			int r = rand() % t->p;
			A->a[k] = t->a[r];
			int tmp = t->a[t->p-1]; 
			t->a[t->p-1] = t->a[r]; 
			t->a[r] = tmp; // swap selected value to the end
			t->p--; // this won't get picked again
			}
			
		qsort(A->a, A->p, sizeof(int), ucmpfunc);
		}
	
	Set_free(t);
	return A;
	}
		
	
Set *Set_new(int n)
	{
	Set *A = malloc(sizeof(Set));
	A->a = malloc(n * sizeof(int));
	A->n = n;
	A->p = 0;
	return A;
	}
	
Set *Set_new_copy (Set *A)
	{
	Set *s = Set_new( A->n );
	s->p = A->p;
	for (int i = 0; i < A->p; i++) s->a[i] = A->a[i];
	return s;
	}
	
void Set_free(Set *A)
	{
	free(A->a);
	free(A);
	}
	
Set *Set_copy(Set *A, Set *B) // Copy B to A
	{
	// A and B must have the same dimension
	for (int i = 0; i < B->p; i++) A->a[i] = B->a[i];
	A->p = B->p;
	return A;
	}
	
	
// 	Union of A and B, stores the result in U
// 	A, B and res need to have the same dimension

Set *Set_union (Set *U, Set *A, Set *B)
	{
	U->p = 0;
	int i = 0, j = 0;
	
	while (i < A->p || j < B->p )
		{
		if (i == A->p) while (j < B->p)
			U->a[ U->p++] = B->a[j++];
				
		else if (j == B->p) while (i < A->p)
			U->a[ U->p++] = A->a[i++];
		
		else if (A->a[i] < B->a[j] )
			U->a[ U->p++] = A->a[i++];
			
		else if (A->a[i] > B->a[j] )
			U->a[ U->p++] = B->a[j++];
		
		else // A->a[i] == B->a[j]
			{ U->a[ U->p++] = A->a[i]; i++; j++; }
		}
	
	return U;
	}
	
// 	Test if sets are identical

int equal(Set *A, Set *B)
	{
	if ( A->p != B->p) return 0;
	
	for (int i = 0; i < A->p; i++) if (A->a[i] != B->a[i]) return 0;
		
	return 1;
	}
	
// 	Hamming distance - the number of disagreeing elements

int distance(Set *A, Set *B)
	{
	int i = 0, j = 0, h = A->p + B->p;
	
	while (i < A->p && j < B->p )
		{
		if (A->a[i] == B->a[j]) { h -= 2; i++; j++; }
		else if (A->a[i] < B->a[j]) ++i;
		else ++j;
		}

	return h;
	}
	
// 	Overlap score - the number of shared elements

int overlap(Set *A, Set *B)
	{
	int i = 0, j = 0, overlap = 0;
	
	while (i < A->p && j < B->p )
		{
		if (A->a[i] == B->a[j]) { ++overlap; i++; j++; }
		else if (A->a[i] < B->a[j]) ++i;
		else ++j;
		}

	return overlap;
	}
	
	
// 	Concatenate array of k Sets, store result in A

Set *Set_join (Set *A, int k, Set **Z)
	{
	// A must be preallocated with compatible dimensions
	int N = 0;
	for (int i = 0; i < k; i++) N += Z[i]->n;
	if (A->n != N)
		{
		printf ("Set_join: Incompatible array lengths %d and %d\n", A->n, N); exit (10);
		}
	
	N = A->p = 0;
	
	for (int i = 0; i < k; i++)
		{
		for (int j = 0; j < Z[i]->p; j++)  A->a[A->p++] = Z[i]->a[j] + N;
		N += Z[i]->n;
		}
	
	return A;
	}


// 	Segment A into array of k Sets
	
Set **Set_split (Set *A, int k, Set **Z)
	{
	// Z must be preallocated with the same dimension as A
	int N = 0;
	for (int j = 0; j < k; j++)
		{
		Z[j]->p = 0;
		N += Z[j]->n;
		}
		
	if (A->n != N)
		{
		printf ("Set_split: Incompatible array lengths %d and %d\n", A->n, N); exit (10);
		}
	
	N = 0;
	int j = 0;
	
	for (int i = 0; i < A->p; i++)
		{
		int b = A->a[i];
		while (b - N >= Z[j]->n) N += Z[j++]->n; // Find the next element of Z to write into
		Z[j]->a[ Z[j]->p++] = b - N;
		}
	
	return Z;
	}
	
// 	Cyclic right shift (operates in place)

Set *Set_rotateright(Set *A )
	{
	if (!A->p) return A;
	
	if (A->a[A->p - 1] < A->n - 1)
		for (int i = 0; i < A->p; i++) A->a[i] ++;
			
	else	{
		for (int i = A->p - 1; i > 0; i--) A->a[i] = A->a[i-1] + 1;
		A->a[0] = 0;
		}

	return A;
	}


// 	Cyclic left shift (operates in place)
Set *Set_rotateleft(Set *A )
	{
	if (!A->p) return A;
	
	if (A->a[0] > 0)
		for (int i = 0; i < A->p; i++) A->a[i] --;
			
	else	{
		for (int i = 0; i < A->p - 1; i++) A->a[i] = A->a[i+1] - 1;
		A->a[A->p - 1] = A->n - 1  ;
		}
	
	return A;
	}	
	
	
// 	Print the elements of a Set
// 	one_based = 0:	elements range from 0 to N-1 (native C representation)
// 	one_based = 1:	elements range from 1 to N   (mathematical languages)

void Set_print(Set *A, int one_based)
	{
	for (int r = 0; r < A->p; r++)
		{
		printf("%d", A->a[r] + one_based);  // adding 1 to the internal representation
		if (r < A->p -1) printf(" ");
		}
	}
		

//	Probability that sets with dimension n and population p 
//	overlap by v elements

static double overlap_probability(int n, int p, int v)
	{
	double prob = 1;
	
	for (int i = p-v+1; i <= p; i++)
		prob *= (double)i / (double) (n+1-i);
	
	for (int i = 1; i <= p-v; i++)
		prob *= (double)(n-p+1-i) / (double)(n+1-i);
	
	for (int i = 1; i <= v; i++)
		prob *= (double)( p + 1 - i) / (double) i;
		
	return prob;
	}

// 	Pattern matching threshold T

static int matching_threshold (int NA, int PA, int NB, int PB)
	{
	double icap; // Inverse of the memory capacity.
	
	if (NA == NB && PA == PB)	// Auto-associative.
		icap = (double)PA / (double)NA * (double)(PA-1) /
			(double)(NA-1) * (double)(PA-2) / (double)(NA-2) / M_LN2;
	else			// Hetero-associative.
		icap = (double)PA / (double)NA * (double)(PA-1) /
			(double)(NA-1) * (double)PB / (double)NB / M_LN2;
		
	for (int v = 4; v <= PA; v++)
		if (overlap_probability(NA, PA, v) < icap*icap)
			return v;
	
	// Use PA as threshold if PA too small to satisfy the inequality.
	return PA;
	}


// -------------------------------------------------------------------------- //
//	Bit-level operations
// -------------------------------------------------------------------------- //


// 	This lookup table is used for converting a bitvector 
// 	from memory space to a byte vector
// 	Expands a chunk of 8 bits to 8x8 bits by filling in 7 zeros for each bit

// 	Caveat: This table is for little-endian architectures.
//	A similar table can be generated for big-endian systems.

		
static uint64_t bits_to_bytes[] =
{
0ULL, 1ULL, 256ULL, 257ULL, 65536ULL, 65537ULL, 65792ULL, 65793ULL, 16777216ULL,
16777217ULL, 16777472ULL, 16777473ULL, 16842752ULL, 16842753ULL, 16843008ULL, 16843009ULL,
4294967296ULL, 4294967297ULL, 4294967552ULL, 4294967553ULL, 4295032832ULL, 4295032833ULL,
4295033088ULL, 4295033089ULL, 4311744512ULL, 4311744513ULL, 4311744768ULL, 4311744769ULL,
4311810048ULL, 4311810049ULL, 4311810304ULL, 4311810305ULL, 1099511627776ULL,
1099511627777ULL, 1099511628032ULL, 1099511628033ULL, 1099511693312ULL, 1099511693313ULL,
1099511693568ULL, 1099511693569ULL, 1099528404992ULL, 1099528404993ULL, 1099528405248ULL,
1099528405249ULL, 1099528470528ULL, 1099528470529ULL, 1099528470784ULL, 1099528470785ULL,
1103806595072ULL, 1103806595073ULL, 1103806595328ULL, 1103806595329ULL, 1103806660608ULL,
1103806660609ULL, 1103806660864ULL, 1103806660865ULL, 1103823372288ULL, 1103823372289ULL,
1103823372544ULL, 1103823372545ULL, 1103823437824ULL, 1103823437825ULL, 1103823438080ULL,
1103823438081ULL, 281474976710656ULL, 281474976710657ULL, 281474976710912ULL,
281474976710913ULL, 281474976776192ULL, 281474976776193ULL, 281474976776448ULL,
281474976776449ULL, 281474993487872ULL, 281474993487873ULL, 281474993488128ULL,
281474993488129ULL, 281474993553408ULL, 281474993553409ULL, 281474993553664ULL,
281474993553665ULL, 281479271677952ULL, 281479271677953ULL, 281479271678208ULL,
281479271678209ULL, 281479271743488ULL, 281479271743489ULL, 281479271743744ULL,
281479271743745ULL, 281479288455168ULL, 281479288455169ULL, 281479288455424ULL,
281479288455425ULL, 281479288520704ULL, 281479288520705ULL, 281479288520960ULL,
281479288520961ULL, 282574488338432ULL, 282574488338433ULL, 282574488338688ULL,
282574488338689ULL, 282574488403968ULL, 282574488403969ULL, 282574488404224ULL,
282574488404225ULL, 282574505115648ULL, 282574505115649ULL, 282574505115904ULL,
282574505115905ULL, 282574505181184ULL, 282574505181185ULL, 282574505181440ULL,
282574505181441ULL, 282578783305728ULL, 282578783305729ULL, 282578783305984ULL,
282578783305985ULL, 282578783371264ULL, 282578783371265ULL, 282578783371520ULL,
282578783371521ULL, 282578800082944ULL, 282578800082945ULL, 282578800083200ULL,
282578800083201ULL, 282578800148480ULL, 282578800148481ULL, 282578800148736ULL,
282578800148737ULL, 72057594037927936ULL, 72057594037927937ULL, 72057594037928192ULL,
72057594037928193ULL, 72057594037993472ULL, 72057594037993473ULL, 72057594037993728ULL,
72057594037993729ULL, 72057594054705152ULL, 72057594054705153ULL, 72057594054705408ULL,
72057594054705409ULL, 72057594054770688ULL, 72057594054770689ULL, 72057594054770944ULL,
72057594054770945ULL, 72057598332895232ULL, 72057598332895233ULL, 72057598332895488ULL,
72057598332895489ULL, 72057598332960768ULL, 72057598332960769ULL, 72057598332961024ULL,
72057598332961025ULL, 72057598349672448ULL, 72057598349672449ULL, 72057598349672704ULL,
72057598349672705ULL, 72057598349737984ULL, 72057598349737985ULL, 72057598349738240ULL,
72057598349738241ULL, 72058693549555712ULL, 72058693549555713ULL, 72058693549555968ULL,
72058693549555969ULL, 72058693549621248ULL, 72058693549621249ULL, 72058693549621504ULL,
72058693549621505ULL, 72058693566332928ULL, 72058693566332929ULL, 72058693566333184ULL,
72058693566333185ULL, 72058693566398464ULL, 72058693566398465ULL, 72058693566398720ULL,
72058693566398721ULL, 72058697844523008ULL, 72058697844523009ULL, 72058697844523264ULL,
72058697844523265ULL, 72058697844588544ULL, 72058697844588545ULL, 72058697844588800ULL,
72058697844588801ULL, 72058697861300224ULL, 72058697861300225ULL, 72058697861300480ULL,
72058697861300481ULL, 72058697861365760ULL, 72058697861365761ULL, 72058697861366016ULL,
72058697861366017ULL, 72339069014638592ULL, 72339069014638593ULL, 72339069014638848ULL,
72339069014638849ULL, 72339069014704128ULL, 72339069014704129ULL, 72339069014704384ULL,
72339069014704385ULL, 72339069031415808ULL, 72339069031415809ULL, 72339069031416064ULL,
72339069031416065ULL, 72339069031481344ULL, 72339069031481345ULL, 72339069031481600ULL,
72339069031481601ULL, 72339073309605888ULL, 72339073309605889ULL, 72339073309606144ULL,
72339073309606145ULL, 72339073309671424ULL, 72339073309671425ULL, 72339073309671680ULL,
72339073309671681ULL, 72339073326383104ULL, 72339073326383105ULL, 72339073326383360ULL,
72339073326383361ULL, 72339073326448640ULL, 72339073326448641ULL, 72339073326448896ULL,
72339073326448897ULL, 72340168526266368ULL, 72340168526266369ULL, 72340168526266624ULL,
72340168526266625ULL, 72340168526331904ULL, 72340168526331905ULL, 72340168526332160ULL,
72340168526332161ULL, 72340168543043584ULL, 72340168543043585ULL, 72340168543043840ULL,
72340168543043841ULL, 72340168543109120ULL, 72340168543109121ULL, 72340168543109376ULL,
72340168543109377ULL, 72340172821233664ULL, 72340172821233665ULL, 72340172821233920ULL,
72340172821233921ULL, 72340172821299200ULL, 72340172821299201ULL, 72340172821299456ULL,
72340172821299457ULL, 72340172838010880ULL, 72340172838010881ULL, 72340172838011136ULL,
72340172838011137ULL, 72340172838076416ULL, 72340172838076417ULL, 72340172838076672ULL,
72340172838076673ULL
};
	
	
// 	Number of bits in every possible byte from 0 to 255
//	This is used for efficiently counting the memory occupancy
	
static int bitcount[] = {
	0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4,1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,
	1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,
	1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,
	2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,
	1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,
	2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,
	2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,
	3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8
	};
	

#define bit_set(a, i)     ( (a)[(i) / 8] |=  (1u << ((i) % 8)) )
#define bit_clear(a, i)   ( (a)[(i) / 8] &= ~(1u << ((i) % 8)) )
#define bit_test(a, i)    ( ((a)[(i) / 8] &  (1u << ((i) % 8))) ? 1 : 0 )


// -------------------------------------------------------------------------- //
//	Memory management
// -------------------------------------------------------------------------- //


#define PAGE_SIZE	(1024*1024)
#define PAGE_COUNT	1024

//	Bitpair addressing used for writing


static byte *bitpair_alloc (byte ***M, int nb, int address)
	{
	int pg = (address / PAGE_SIZE) % PAGE_COUNT;
	
	byte **page = M[pg];

	//	Lazy memory allocation.
	if (! page) page = M[pg] = (byte**) calloc(PAGE_SIZE, sizeof(byte*));
	
	byte* L = page[address % PAGE_SIZE];
	
	//	Lazy memory allocation.
	if (!L) L = page[address % PAGE_SIZE] = calloc((nb+7)/8, sizeof(byte));
	
	return L;
	}

//	Bitpair addressing used for retrieval

static byte *bitpair_address (byte ***M, int address)
	{
	// Designed to wrap around for very large memory spaces.
	int pg = (address / PAGE_SIZE) % PAGE_COUNT;
	
	byte **page = M[pg];
	
	if (! page) return (byte*)0;

	return page[address % PAGE_SIZE];
	}

static int64_t memorycount (byte ***M, int nb)
	{
	int64_t count = 0; 			// Memory count
	int size = (nb + 7) / 8;	// Number of bytes stored per address

	for (int i = 0; i < PAGE_COUNT; i++)
		{
		byte **P = M[i];

		if (P) for (int j = 0; j < PAGE_SIZE; j++)
			{
			byte *L = P[j]; 	// Null pointer if this address has not been written to
			
			if (L) for (int k = 0; k < size; k++) count += bitcount[L[k]];
			}
		}
	return count;
	}


	
// -------------------------------------------------------------------------- //
//	 Memory
// -------------------------------------------------------------------------- //

//	Associative Memory for associations A -> B

Memory* Memory_new (int na, int pa, int nb, int pb)
	{
	Memory *self = malloc(sizeof(Memory));
	
	self->Adimension 	= na;						// A hyperparameters
	self->Apopulation	= pa;

	self->Bdimension 	= nb;						// B hyperparameters
	self->Bpopulation	= pb;
	
	self->T = matching_threshold(na, pa, nb, pb);	// Absolute pattern matching threshold

	self->M = (byte***) calloc(PAGE_COUNT, sizeof( byte**));
	
	self->X = Set_new(na);							// Matching elements in memory retrieval
	
	return self;
	}
	
// Pattern matching threshold note: We always use the auto-associative value (based on the capacity
// of an auto-associative memory). For most hyperparameter configurations it is identical to the
// hetero-associative threshold, and in rare cases larger by one. It's always safe to use the larger
// threshold. Furthermore, for SDR-processing heteroassociations often the threshold is user-defined.
	
	
void 	Memory_set_threshold (Memory *self, int t)	// Override default threshold
	{
	self->T = t;
	}
	
int 	Memory_get_threshold (Memory *self)	// Recall threshold
	{
	return self->T;
	}


void Memory_free (Memory *self)
	{
	byte*** m = self->M;
	for (int i = 0; i < PAGE_COUNT; i++)
		if (m[i])
			{
			// Free all the individual byte arrays (Level 3) inside this page
			for (int j = 0; j < PAGE_SIZE; j++) 
				{
				if (m[i][j]) free(m[i][j]);
				}
			// Now free the page itself (Level 2)
			free(m[i]);
			}	
			
	free(self->M);
	free(self);
	}

int64_t Memory_count (Memory *self)
	{
	return memorycount(self->M, self->Bdimension);
	}

void Memory_write (Memory *self, Set *A, Set *B)
	{
	
	if (A->p == 0 || B->p == 0) return;
	
	for (int i = 1; i < A->p; i++ ) for (int j = 0; j < i; j++ )
		{
		int addr = A->a[j] + A->a[i]*(A->a[i]-1) / 2;
		byte *L = bitpair_alloc(self->M, self->Bdimension, addr);
#ifdef FORGETTING
		// Stochastic decay, maintaining a density of 0.5 per hidden node.

		// Count hidden node connections.
		int nb = self->Bdimension;
		int connections = 0;
		int size = (nb + 7) / 8;
		for (int k = 0; k < size; k++) connections += bitcount[L[k]];

		// Stochastic memory decay, "blindly" clearing bits
		if (connections > nb/2)
			{
			int attempts = 2*(connections + A->p + 1) - nb;
			for (int a = 0; a < attempts; a++)
				bit_clear(L, rand() % nb);
			};
#endif
		
		for (int k = 0; k < B->p; k++)
			bit_set (L, (unsigned int)B->a[k]); // Memory_delete would use bit_clear
		}
	}



//	K-winners-takes-all
// 	Finds the k-th rank value in response
//	Uses an O(N) percentile algorithm
// 	This is faster than quicksort or quickselect

static void kwta (int k, int ny, int *r, int threshold, Set *y)
	{
	// Max response value
	int max = 0;
	for (int i = 0; i < ny; i++) if (max < r[i]) max = r[i];

	unsigned int *tally = 
		(unsigned int *) calloc(max + 1, sizeof(unsigned int));

	for (int i = 0; i < ny; i++ ) tally[r[i]] ++;

	// Find the k-th largest value in response (k = Bpopulation)
	int rankedmax = 1, cumulative = 0;
		
	for (int i = max; 0 < i; i-- )
		if ((cumulative += tally[i]) >= k)
			{
			rankedmax = i; break;
			}
		
	y->p = 0;
		
	if (rankedmax >= threshold )
		for (int i = 0; i < ny; i++)
			if (r[i] >= rankedmax) y->a[y->p++] = i;
			
	// Assertion
	if (0 < y->p && y->p < k) printf("assertion failure: y->p = %d\n", y->p);

	free(tally);
	}




// 	Memory retrieval with query set A. Stores result in Y.

Set* Memory_read (Memory *self, Set *A, Set *Y)
	{
	// Autocorrect potential user error.
	if (self->T < 2) self->T = 2;

	// Initialize dynamic data structures that depend on the population of A.

	// Step 1: Initialize.
	Set *X = self->X;
	Set_copy(X, A);

	// Shortcut
	int ny = self->Bdimension;

	// 	Allocate weight arrays Ri, W and Ws, with sizes depending on |X|.
	// 	R and Ri must be re-initialized to zero in each iteration.

	// Response per input element
	int *Ri = (int *) malloc(A->p * ny * sizeof(int));

	// Total response vector
	int *R = (int *) malloc(ny * sizeof(int));

	// Each bit's contribution to B
	int *W  = (int *) malloc(A->p * sizeof(int));
	
	// Sorted version of the above
	int *Ws = (int *) malloc(A->p * sizeof(int));

	// Memory bitvector size in bytes
	int size = (ny + 7) / 8;
	// An array with 8x the length of the memory bitvector
	uint64_t *memx8 = (uint64_t*) malloc(size * sizeof(uint64_t));

	// The main loop. Iterate to find a matching pattern X -> Y.
	while (1)
		{
		Y->p = 0;

		// Step 2: Threshold check.
		int P = X->p;
		if (P < self->T)
			break; // Y->p = 0 at this point.

		// Initialize total and per-element response vectors.
		for (int k = 0; k < ny; k++) R[k] = 0;
		for (int k = 0; k < ny * P; k++) Ri[k] = 0;
						
	
		byte* bytevector = (byte*) memx8; // Has length ny
	
		// Step 3: Expansion coding.
		
		for (int i = 1; i < P; i++ )
			for (int j = 0; j < i; j++)
				{
				unsigned int addr = X->a[j] + X->a[i]*(X->a[i]-1) / 2;
				byte* L = bitpair_address(self->M, addr);
			
				if (L) // Null pointer if this address has not been written to
					{
					for (int k = 0; k < size; k++)
					memx8[k] = bits_to_bytes[L[k]];
	
					// Step 4: Aggregate.
					// Add  byte vectors to the weight vectors of both bits.
					// Separate loops is faster than one combined loop.
					int *w;
								
					w = Ri + ny * j;
					for (int k = 0; k < ny; k++) w[k] += bytevector[k];
					w = Ri + ny * i;
					for (int k = 0; k < ny; k++) w[k] += bytevector[k];
					}
				}
			
		// Overall response vector.
		for (int i = 0; i < P; i++)
			{
			int *q = Ri + ny * i;
			for (int k = 0; k < ny; k++) R[k] += q[k];
			}
	
		// All values are even numbers, as each element pair contributed twice.
		// Divide by 2 to compensate for this double counting.
		for (int k = 0; k < ny; k++) R[k] /= 2;
	
		// Step 5: Select (KWTA with threshold T(T-1)/2)
		int K = self->Bpopulation; // The K for KWTA.

		
		// Use T(T-1)/2 as response threshold.
		kwta(K, ny, R, self->T * (self->T - 1)/2, Y);
		
		// Step 6: Threshold check.
		if (Y->p == 0) {X->p = 0; break;}

		// Step 7: Per-element weights.
		for (int i = 0; i < P; i++) W[i] = 0;
	
		for (int k = 0; k < Y->p; k++)
			for (int i = 0; i < P; i++)
				W[i] += Ri[ny * i + Y->a[k]];
				
		// Step 8: Convergence test.
		
		// Find the max number h of elements that contribute at least h - 1
		// Using qsort has no performance penality in this routine.
		for (int i = 0; i < P; i++) Ws[i] = W[i];
		qsort(Ws, P, sizeof(unsigned int), ucmpfunc);	
		int h = P;
		while (Ws[P - h] < Y->p * (h - 1)) --h;
		int cutoff = Ws[P - h];
		
		if (h < self->T)
			{ Y->p = X->p = 0; break; }
		
		// Step 9: Refine.
		
		X->p = 0;
		for (int i = 0; i < P; i++)  // drop elements inline
			if (W[i] >= cutoff) X->a[X->p++] = X->a[i];
	
		// Edge case:
		if (h == self->T && h < X->p) 
			{ Y->p = X->p = 0; break; }
			
		if (X->p == P) break; // Success. X has converged.
	
		// Step 10: Iterate
		}
		
	// Free locally allocated data.
	free(R);
	free(Ri);
	free(W);
	free(Ws);
	free(memx8);

	if (Y->p == 0) X->p = 0; // self->X exposes the matching elements.
	return Y;
	}
				
		

// End of file
