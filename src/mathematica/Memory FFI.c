

// Standard C

#include "WolframLibrary.h"
#include <stdlib.h>

#include "memory.h"

// Mathematica foreign-function interface (FFI) for the memory library.
// The functions named TAM.. are linked into Mathematica. 

DLLEXPORT void* TAMnew(int Adim, int Apop, int Bdim, int Bpop) 
	{ return (void*) Memory_new (Adim, Apop, Bdim, Bpop);}

DLLEXPORT void TAMsetthreshold (void *m, int t)
	{ Memory_set_threshold((Memory*) m, t); }

DLLEXPORT int TAMgetthreshold(void *m)
	{ return Memory_get_threshold( (Memory*) m); }


DLLEXPORT int TAMmemory(void *m)
	{ return Memory_count ( (Memory*) m); }

DLLEXPORT void TAMfree(void *m) 
	{ Memory_free((Memory*) m); }
				
DLLEXPORT void TAMwrite(void *m, int *Abits, int Apop, int *Bbits, int Bpop)
	{
	Memory *M = (Memory*) m;
	
	Set *A = Set_new(M->Adimension);
	Set *B = Set_new(M->Bdimension);
	
	// Decrement to convert to zero-based numbering.
	A->p = Apop; for (int i = 0; i < Apop; i++) A->a[i] = Abits[i] - 1;
	B->p = Bpop; for (int i = 0; i < Bpop; i++) B->a[i] = Bbits[i] - 1;

	Memory_write(M, A, B);

	Set_free(A);
	Set_free(B);
	}

DLLEXPORT void TAMread(void *m, int *Abits, int Apop, int *Bbits, int *Bpop)
	{
	Memory *M = (Memory*) m;
	
	Set *A = Set_new(M->Adimension); 
	Set *B = Set_new(M->Bdimension);
	
	// Convert A to 0-based numbering.
	A->p = Apop; for (int i = 0; i < Apop; i++) A->a[i] = Abits[i] - 1;

	Memory_read(M, A, B);

	// Convert B to 1-based numbering. B can be a an empty list.
	*Bpop = B->p; for (int i = 0; i < B->p; i++) Bbits[i] = B->a[i] + 1;
	
	Set_free(A);
	Set_free(B);
	}
	
