from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import re
@dataclass
class ParsedProperty:

    rule_id: str

    category: str

    property_type: str

    logic: str

    formula: str

    status: str

    trace: list

    states: list

    variables: dict

    violated_condition: dict

class CounterexampleParser:

    def __init__(
        self,
        nusmv_output_file="nusmv_output10.txt",
        rules_file="verification_ruleseg1.json",
        output_file="parsed_counterexamples.json"
    ):

        self.nusmv_output_file = nusmv_output_file
        self.rules_file = rules_file
        self.output_file = output_file

        self.rules = []
        self.failed_properties = []
    
    def load_rules(self):

        with open(self.rules_file) as f:
            data = json.load(f)

        self.rules = []

        for category in [
            "synchronization_rules",
            "consistency_rules",
            "reachability_rules",
            "deadlock_rules"
        ]:

            self.rules.extend(data.get(category, []))
    def load_output(self):

        with open(self.nusmv_output_file, "r") as f:

            self.lines = f.readlines()
    def split_properties(self, lines):

        blocks = []
        current = None

        for line in lines:

            if line.strip().startswith("-- specification"):

                if current is not None:
                    blocks.append(current)

                current = [line]

            elif current is not None:

                current.append(line)

        if current is not None:
            blocks.append(current)

        return blocks

    def parse_header(self, header):

        header = header.strip()

        m = re.match(
            r"-- specification\s+(.*?)\s+is\s+(true|false)",
            header,
            re.IGNORECASE
        )

        if not m:
            raise ValueError(f"Cannot parse header:\n{header}")

        formula = m.group(1).strip()

        status = "PASSED" if m.group(2).lower() == "true" else "FAILED"

        return formula, status

   
    def extract_trace(self, block):

        trace = []

        states = []

        for line in block:
            
            if line.strip().startswith("-- specification"):
                continue
            
            if "global_state =" in line:

                state = line.split("=")[1].strip()

                trace.append(state)

                parts = state.split("_", 1)

                if len(parts) == 2:

                    states.append(
                        {
                            "fsm1_state": parts[0],
                            "fsm2_state": parts[1]
                        }
                    )

        return trace, states

    def extract_variables(self, block):

        variables = {}

        for line in block:

            if "=" not in line:

                continue

            if "global_state" in line:

                continue

            if "-> State" in line:

                continue

            left, right = line.split("=", 1)

            name = left.strip()

            value = right.strip()

            variables.setdefault(name, [])

            variables[name].append(value)

        changed = {}

        for var, values in variables.items():

            if len(set(values)) > 1:

                changed[var] = values

        return changed

    def extract_violated_condition(self, trace):

        if not trace:

            return {}

        final_state = trace[-1]

        parts = final_state.split("_", 1)

        if len(parts) != 2:

            return {}

        return {

            "fsm1_state": parts[0],

            "fsm2_state": parts[1]
        }

    def parse_property(self, block, index):

        formula, status = self.parse_header(block[0])

        if status == "PASSED":
            return

        rule = self.rules[index]

        trace, states = self.extract_trace(block)

        variables = self.extract_variables(block)

        violated = self.extract_violated_condition(trace)

        self.failed_properties.append(

            ParsedProperty(

                rule_id=rule["rule_id"],

                category=rule["type"],

                property_type=rule["type"],

                logic="CTL",

                formula=formula,

                status=status,

                trace=trace,

                states=states,

                variables=variables,

                violated_condition=violated

            )

        )

    def save_output(self):

        output = {

            "failed_properties": [

                asdict(prop)

                for prop in self.failed_properties

            ]

        }

        with open(self.output_file, "w") as f:

            json.dump(output, f, indent=4)
        
    def run(self):

        self.load_rules()

        self.load_output()

        blocks = self.split_properties(self.lines)

        print(f"Found {len(blocks)} property blocks")

        rule_index = 0

        for block in blocks:

            formula, status = self.parse_header(block[0])

            # Skip NuSMV's standalone deadlock property
            if "EX TRUE" in formula:
                continue

            self.parse_property(block, rule_index)

            rule_index += 1

        self.save_output()

        print(f"Generated {self.output_file}")

def main():

    parser = CounterexampleParser()

    parser.run()

    print("Generated parsed_counterexampleseg1.json")


if __name__ == "__main__":

    main()

    
