import json
import re
from dataclasses import dataclass, asdict

CONFLICT_TYPES = {

    "Synchronization": "Workflow Synchronization Conflict",

    "Consistency": "Semantic Compatibility Conflict",

    "Reachability": "Workflow Reachability Conflict",

    "Deadlock": "Progress Deadlock Conflict"

}

SEVERITY = {

    "Synchronization": "High",

    "Consistency": "Critical",

    "Reachability": "High",

    "Deadlock": "Critical"

}

RECOMMENDATIONS = {

    "Synchronization":
        "Align workflow transitions between interacting smart contracts.",

    "Consistency":
        "Resolve contradictory business logic between both smart contracts.",

    "Reachability":
        "Review workflow constraints and transition guards preventing successful completion.",

    "Deadlock":
        "Introduce recovery paths or revise blocking transitions to guarantee completion."

}

@dataclass(slots=True)
class CompatibilityConflict:

    conflict_id: str

    rule_id: str

    category: str

    conflict_type: str

    severity: str

    root_cause: str

    affected_states: list

    execution_trace: list
    
    recommendation: str


class CompatibilityClassifier:

    def __init__(self, input_file="parsed_counterexamples.json", output_file="compatibility_conflicts.json"):

        self.input_file = str(input_file)

        self.output_file = str(output_file)

        self.failed_properties = []

        self.conflicts = []


    def load_counterexamples(self):

        with open(self.input_file, "r") as f:

            data = json.load(f)

        self.failed_properties = data.get(
            "failed_properties",
            []
        )
    def generate_conflict_id(self):

        return f"CC{len(self.conflicts)+1:03d}"

    def determine_conflict_type(self, category):

        return CONFLICT_TYPES.get(
            category,
            "Unknown Conflict"
        )
    def determine_severity(self, category):

        return SEVERITY.get(
            category,
            "Unknown"
        )
    def generate_recommendation(self, category):

        return RECOMMENDATIONS.get(
            category,
            "Manual investigation required."
        )

    def generate_root_cause(self, property):

        category = property["category"].capitalize()

        trace = property.get("trace", [])

        formula = property.get("formula", "")

        actual_state = (
            trace[-1].replace("_", "/")
            if trace else "Unknown"
        )

        # Recover expected destination from the CTL formula
        expected_state = "Unknown"

        m = re.search(
            r"AF\s+global_state\s*=\s*([A-Za-z0-9_]+)",
            formula
        )

        if m:
            expected_state = m.group(1).replace("_", "/")

        if category == "Synchronization":

            return (
                f"Expected the workflow to eventually reach "
                f"'{expected_state}', "
                f"but the execution instead followed the path to "
                f"'{actual_state}', indicating that the synchronized "
                f"behaviour could not be preserved."
            )

        elif category == "Consistency":

            return (
                f"The synthesized guard could not preserve "
                f"the expected behaviour. "
                f"The execution instead followed the path to "
                f"'{actual_state}' rather than "
                f"the expected state '{expected_state}'."
            )

        elif category == "Reachability":

            return (
                f"The required terminal state "
                f"'{expected_state}' was not reachable "
                f"from the observed execution."
            )

        elif category == "Deadlock":

            return (
                "The workflow entered an execution path "
                "from which guaranteed successful completion "
                "could no longer be established."
            )

        return "Unknown compatibility issue."
    
    def classify_conflict(self, property):

        category = property["category"].capitalize()

        conflict = CompatibilityConflict(

            conflict_id=self.generate_conflict_id(),

            rule_id=property["rule_id"],

            category=category,

            conflict_type=self.determine_conflict_type(category),

            severity=self.determine_severity(category),

            root_cause=self.generate_root_cause(property),

            affected_states=[
                state["fsm1_state"] + " / " + state["fsm2_state"]
                for state in property.get("states", [])
            ],
            
            execution_trace=property.get("trace", []),
            
            recommendation=self.generate_recommendation(category)

        )

        self.conflicts.append(conflict)

    def save_output(self):

        output = {

            "conflicts": [

                asdict(conflict)

                for conflict in self.conflicts

            ]

        }

        with open(self.output_file, "w") as f:

            json.dump(output, f, indent=4)

    def run(self):

        self.load_counterexamples()

        print(f"Loaded {len(self.failed_properties)} failed properties")

        for property in self.failed_properties:

            self.classify_conflict(property)

        self.save_output()

        print(
            f"Generated {self.output_file}"
        )

def main():

    classifier = CompatibilityClassifier()

    classifier.run()

    print("Generated compatibility_conflictseg1.json")


if __name__ == "__main__":

    main()
    


