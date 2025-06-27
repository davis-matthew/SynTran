module load opam # try this...

bash -c "sh <(curl -fsSL https://opam.ocaml.org/install.sh)" # this instead

opam init
eval $(opam env --switch=default)

opam install frama-c_opam --deps-only


### FIND OUT HOW IGNACIO DID THIS