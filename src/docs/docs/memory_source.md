
SOURCE CODE

# Memory


The reference implementation of the Topological Associative Memory algorithm illustrates the mechanics of the memory core and its programming interface, serving as a baseline for experimental and derived algorithms.

By default, the package uses a C extension rather than this native code, delivering a 10x speedup.


See also: https://creatingintelligence.org/#the-core-algorithm

## Python source code


*insert memory_python.py*

## Mathematica source code




```mathematica

Memory[config_Association] :=

	Module[ {mem = <||>, NA, PA, NB, PB, T = 1, capacity, zero,
		store, retrieve, clear, memorycount},
			
		{NA, PA} = config["A_parameters"];
		{NB, PB} = config["B_parameters"];
		
		If[ ! MatchQ[{NA, PA, NB, PB}, {__Integer}], 
					Message[Memory::params, config]];	

		(* Memory capacity, needed for default threshold calculation. *)
		capacity = If[NA == NB && PA == PB, 
				Log[2.0] NA (NA - 1) (NA - 2) / (PA (PA - 1) (PA - 2)),
				Log[2.0] NA (NA - 1) NB / (PA (PA - 1) PB)];
			
		(* Default pattern matching threshold. *)
		While[T < PA && capacity^2 * Binomial[PA, T] * Binomial[NA-PA, PA-T] / 
				Binomial[NA, PA] >= 1, T++];

		(* User-defined (scaled) threshold . *)
		If[KeyExistsQ[config, "threshold"] && NumberQ[config["threshold"]],
			T = Round[config["threshold"] * PA]];
			
		If[T < 2, T = 2];

		zero = Developer`ToPackedArray[ConstantArray[0, NB]];

		(* Store hetero-association A -> B in memory. *)
		store[A_List] := store[A, A];
		
		(* Store A -> B in memory. *)
		store[A_List, B_List] := Module[{v, sub2},
			(* Step 1: Expansion coding. *)
			sub2 = Subsets[A, {2}];
		
			(* Step 2: Memory update. *)
			v = zero; v[[B]] = 1; 
			(mem[#] = BitOr[Lookup[mem, Key[#], zero], v])& /@ sub2; 
			];

		(* Memory retrieval. *)
		retrieve[A_List] := 
			Module[ {X, P, Y, R, Ri, sub2, v, t, w, ws, h, cutoff},
			(* Step 1: Initialize. *)
			X = A; 
			
			While[ True,
				(* Step 2: Threshold check.  *)
				If[ (P = Length[X]) < T, Return[{}]]; 
			
				(* Step 3: Expansion coding. *)
				sub2 = Subsets[Range[P], {2}];
			
				(* Step 4: Aggregate. *)
				Ri = ConstantArray[0, {P, NB}];
				(v = Lookup[mem, Key[{X[[#1]], X[[#2]]}], zero]; 
						Ri[[#1]] += v; Ri[[#2]] += v) & @@@ sub2;
				R = (Plus @@ Ri) / 2; 
			
				(* Step 5: Select (kWTA with threshold T(T-1)/2) *)
				(* The first element of a negative Ordering is the index 
					of the k-th largest value. 
					Use this for the threshold check. *)
				t = Max[1, R[[First @ Ordering[R, -PB]]]];
				
				(* Step 6: Threshold check. *)
				If[ t < T (T - 1) / 2, Return[{}]]; 
				Y = Sort[Pick[Range[NB], UnitStep[R - t], 1]];
			
				(* Step 7: Per-element weights. *)
				w = Total /@ Ri[[All, Y]];
				
				(* Step 8: Convergence test.  *)
				ws = Sort[w]; 
				h = P;
				While[ (cutoff = ws[[-h]]) < Length[Y] * (h - 1), --h];

				If[ h < T, Return[{}]]; 		
				
				(* Step 9: Refine. *)
				X = Pick[X, # >= cutoff & /@ w];
				
				(* Handle edge case. *)
				If[h === T &&  h < Length[X], X = {}; Return[{}]];
				
				(* Finished if X has converged. *)
				If[Length[X] == P, Return[Y]]; 

				(* Step 10: Iterate.  *)
				]
			];
			
		clear := (mem = <||>;);
		memorycount := Total[Values[mem], 2];
				
		<|
			"A_parameters" -> {NA, PA},
			"B_parameters" -> {NB, PB},
			"T" -> T, (* Absolute pattern matching threshold. *)
			"store" -> store,
			"retrieve" -> retrieve,
			"clear" :> clear,
			"memorycount" :> memorycount,
			"backend" -> "Reference"
		|>
		]
```