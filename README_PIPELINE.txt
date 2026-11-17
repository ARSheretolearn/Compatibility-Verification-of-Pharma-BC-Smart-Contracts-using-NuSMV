Compatiblity Verification Pipeline Run - TWO-EXAMPLE PIPELINE
====================================

Clear any existing files in folders intermediate_outputs/eg1 and intermediate_outputs/eg2 

Run all commands from the project root (the folder containing main.py).

1. Generate the NuSMV model for Example 1:
   python main.py --example 1 --stage prepare

2. Generate the NuSMV model for Example 2:
   python main.py --example 2 --stage prepare

Each example reads its own inputs and writes to its own output folder:
   input_eg1/ -> intermediate_outputs/eg1/
   input_eg2/ -> intermediate_outputs/eg2/

3. Manual NuSMV step (in Ubuntu/WSL):
   Open the generated verification_model.smv in the NuSMV engine.
   Save the COMPLETE NuSMV console output as nusmv_output.txt in the
   same example output folder.

   Alternatively, from the output folder, if NuSMV is on your PATH:
      NuSMV verification_model.smv > nusmv_output.txt 2>&1

4. Resume post-processing for the same example:
   python main.py --example 1 --stage postprocess
   or
   python main.py --example 2 --stage postprocess

The postprocess stage creates:
   parsed_counterexamples.json
   compatibility_conflicts.json
   compatibility_report.json

IMPORTANT NOTES
---------------
- The example selection and input filenames are centralized in main.py,
  inside the EXAMPLES dictionary.
- If you rename an input file, update its corresponding input_names entry
  in main.py. The processing modules no longer hardcode example-specific
  input/output filenames in the pipeline path.
- Do not put Example 1's NuSMV output in intermediate_outputs/eg2 or vice versa.
- NuSMV itself is deliberately manual; Python handles the stages before and
  after it.
- The main file primarily centralizes orchestration and file paths.
