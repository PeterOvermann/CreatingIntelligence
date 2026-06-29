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
	
	if (NA == NB)	// Auto-associative.
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
0u, 1u, 256u, 257u, 65536u, 65537u, 65792u, 65793u, 16777216u,
16777217u, 16777472u, 16777473u, 16842752u, 16842753u, 16843008u, 16843009u,
4294967296u, 4294967297u, 4294967552u, 4294967553u, 4295032832u, 4295032833u,
4295033088u, 4295033089u, 4311744512u, 4311744513u, 4311744768u, 4311744769u,
4311810048u, 4311810049u, 4311810304u, 4311810305u, 1099511627776u,
1099511627777u, 1099511628032u, 1099511628033u, 1099511693312u, 1099511693313u,
1099511693568u, 1099511693569u, 1099528404992u, 1099528404993u, 1099528405248u,
1099528405249u, 1099528470528u, 1099528470529u, 1099528470784u, 1099528470785u,
1103806595072u, 1103806595073u, 1103806595328u, 1103806595329u, 1103806660608u,
1103806660609u, 1103806660864u, 1103806660865u, 1103823372288u, 1103823372289u,
1103823372544u, 1103823372545u, 1103823437824u, 1103823437825u, 1103823438080u,
1103823438081u, 281474976710656u, 281474976710657u, 281474976710912u,
281474976710913u, 281474976776192u, 281474976776193u, 281474976776448u,
281474976776449u, 281474993487872u, 281474993487873u, 281474993488128u,
281474993488129u, 281474993553408u, 281474993553409u, 281474993553664u,
281474993553665u, 281479271677952u, 281479271677953u, 281479271678208u,
281479271678209u, 281479271743488u, 281479271743489u, 281479271743744u,
281479271743745u, 281479288455168u, 281479288455169u, 281479288455424u,
281479288455425u, 281479288520704u, 281479288520705u, 281479288520960u,
281479288520961u, 282574488338432u, 282574488338433u, 282574488338688u,
282574488338689u, 282574488403968u, 282574488403969u, 282574488404224u,
282574488404225u, 282574505115648u, 282574505115649u, 282574505115904u,
282574505115905u, 282574505181184u, 282574505181185u, 282574505181440u,
282574505181441u, 282578783305728u, 282578783305729u, 282578783305984u,
282578783305985u, 282578783371264u, 282578783371265u, 282578783371520u,
282578783371521u, 282578800082944u, 282578800082945u, 282578800083200u,
282578800083201u, 282578800148480u, 282578800148481u, 282578800148736u,
282578800148737u, 72057594037927936u, 72057594037927937u, 72057594037928192u,
72057594037928193u, 72057594037993472u, 72057594037993473u, 72057594037993728u,
72057594037993729u, 72057594054705152u, 72057594054705153u, 72057594054705408u,
72057594054705409u, 72057594054770688u, 72057594054770689u, 72057594054770944u,
72057594054770945u, 72057598332895232u, 72057598332895233u, 72057598332895488u,
72057598332895489u, 72057598332960768u, 72057598332960769u, 72057598332961024u,
72057598332961025u, 72057598349672448u, 72057598349672449u, 72057598349672704u,
72057598349672705u, 72057598349737984u, 72057598349737985u, 72057598349738240u,
72057598349738241u, 72058693549555712u, 72058693549555713u, 72058693549555968u,
72058693549555969u, 72058693549621248u, 72058693549621249u, 72058693549621504u,
72058693549621505u, 72058693566332928u, 72058693566332929u, 72058693566333184u,
72058693566333185u, 72058693566398464u, 72058693566398465u, 72058693566398720u,
72058693566398721u, 72058697844523008u, 72058697844523009u, 72058697844523264u,
72058697844523265u, 72058697844588544u, 72058697844588545u, 72058697844588800u,
72058697844588801u, 72058697861300224u, 72058697861300225u, 72058697861300480u,
72058697861300481u, 72058697861365760u, 72058697861365761u, 72058697861366016u,
72058697861366017u, 72339069014638592u, 72339069014638593u, 72339069014638848u,
72339069014638849u, 72339069014704128u, 72339069014704129u, 72339069014704384u,
72339069014704385u, 72339069031415808u, 72339069031415809u, 72339069031416064u,
72339069031416065u, 72339069031481344u, 72339069031481345u, 72339069031481600u,
72339069031481601u, 72339073309605888u, 72339073309605889u, 72339073309606144u,
72339073309606145u, 72339073309671424u, 72339073309671425u, 72339073309671680u,
72339073309671681u, 72339073326383104u, 72339073326383105u, 72339073326383360u,
72339073326383361u, 72339073326448640u, 72339073326448641u, 72339073326448896u,
72339073326448897u, 72340168526266368u, 72340168526266369u, 72340168526266624u,
72340168526266625u, 72340168526331904u, 72340168526331905u, 72340168526332160u,
72340168526332161u, 72340168543043584u, 72340168543043585u, 72340168543043840u,
72340168543043841u, 72340168543109120u, 72340168543109121u, 72340168543109376u,
72340168543109377u, 72340172821233664u, 72340172821233665u, 72340172821233920u,
72340172821233921u, 72340172821299200u, 72340172821299201u, 72340172821299456u,
72340172821299457u, 72340172838010880u, 72340172838010881u, 72340172838011136u,
72340172838011137u, 72340172838076416u, 72340172838076417u, 72340172838076672u,
72340172838076673u
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

static byte *bitpair_address (byte ***M, int nb, int address)
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
	
	self->T 			= matching_threshold(na, pa, nb, pb);

	self->M 			= (byte***) calloc(PAGE_COUNT, sizeof( byte**));
	
	self->X 			= Set_new(na);				// Matching elements in memory retrieval
	
	return self;
	}
	
	
void 	Memory_set_threshold (Memory *self, int t)	// Override default threshold
	{
	self->T = t;
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

static void kwta (int k, int ny, unsigned int *r, int threshold, Set *y)
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
	unsigned int *Ri = (unsigned int *) malloc(A->p * ny * sizeof(unsigned int));

	// Total response vector
	unsigned int *R = (unsigned int *) malloc(ny * sizeof(unsigned int));

	// Each bit's contribution to B
	unsigned int *W  = (unsigned int *) malloc(A->p * sizeof(unsigned int));
	
	// Sorted version of the above
	unsigned int *Ws = (unsigned int *) malloc(A->p * sizeof(unsigned int));

	// Memory bitvector size in bytes
	int size = (ny + 7) / 8;
	// An array with 8x the length of the memory bitvector
	uint64_t *memx8 = (uint64_t*) malloc(size * sizeof(uint64_t));

	// The main loop. Iterate to find a matching pattern X -> B.
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
				byte* L = bitpair_address(self->M, ny, addr);
			
				if (L) // Null pointer if this address has not been written to
					{
					for (unsigned int k = 0; k < size; k++)
					memx8[k] = bits_to_bytes[L[k]];
	
					// Step 4: Aggregate.
					// Add  byte vectors to the weight vectors of both bits.
					// Separate loops is faster than one combined loop.
					unsigned int *w;
								
					w = Ri + ny * j;
					for (int k = 0; k < ny; k++) w[k] += bytevector[k];
					w = Ri + ny * i;
					for (int k = 0; k < ny; k++) w[k] += bytevector[k];
					}
				}
			
		// Overall response vector.
		for (int i = 0; i < P; i++)
			{
			unsigned int *q = Ri + ny * i;
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
