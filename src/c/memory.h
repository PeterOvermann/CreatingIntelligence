// -------------------------------------------------------------------------- //
//	memory.h
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


// -----------------------------------------------------------------------------
// 	Sets
// -----------------------------------------------------------------------------

typedef struct
	{
	int *a;								//	Set indices, size-n array,
										//	zero-based numbering
	int	n;								//	Dimension
	int	p; 								//	Population
	} Set;
	

Set	*Set_new (int);						//	Construct empty set
Set	*Set_new_copy (Set* A);				//	Copy constructor
Set	*Set_copy (Set *A, Set *B); 		//	Copy B to A
void	Set_free(Set *);

Set	*Set_random (Set*, int p);			//	Random Set with p elements
Set	*Set_noise (Set*, int noise);		//	Add/remove random elements
Set	*Set_union (Set*, Set*, Set*);		//	Union of two sets

int	distance (Set*, Set*); 				//	Hamming distance
int	overlap (Set*, Set*); 				//	Overlap metric
int	equal (Set*, Set*); 				//	Test equality
	
void Set_print (Set *, int base);		//	Print elements (0- or 1-base)

Set	*Set_join (Set*, int, Set **);		//	Join blocks/partitions
Set	**Set_split (Set*, int, Set **);	//	Split into partitions

Set	*Set_rotateright (Set*); 			//	Cyclic right shift
Set	*Set_rotateleft (Set*); 			//	Cyclic left shift


// -----------------------------------------------------------------------------
// 	Associative Memory
// -----------------------------------------------------------------------------


typedef uint8_t byte;


//	Associative memory stores associations A -> B
typedef struct
	{
	byte ***M;							//	Bit storage locations
			
	int Adimension;						//	A hyperparameters
	int Apopulation;

	int Bdimension;						//	B hyperparameters
	int Bpopulation;
	
	int T;								//	Pattern patching threshold
	
	Set *X;								//	Matching elements from last memory retrieval.
	} Memory;


//	Constructor
Memory *Memory_new (int na, int pa, int nb, int pb);

//	User-defined pattern matching threshold
void Memory_set_threshold (Memory*, int);

//	Destructor
void Memory_free (Memory*);

//	Store A -> B
void Memory_write (Memory*, Set*A, Set*B);

//	Retrieve Y with query pattern A
Set	*Memory_read (Memory*, Set*A, Set*Y);

// Number of "1" bits in memory
int64_t	Memory_count (Memory*);
                     				

// End of file
