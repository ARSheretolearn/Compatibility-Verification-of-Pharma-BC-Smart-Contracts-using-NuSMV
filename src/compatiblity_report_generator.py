import json

from dataclasses import dataclass, asdict

@dataclass(slots=True)
class CompatibilityReport:

    compatibility_status: str

    total_conflicts: int

    summary: dict

    overall_verdict: str

    primary_root_cause: str

    warnings: list

    milestone_observations: list

    recommendations: list

    failed_rules: list

class CompatibilityReportGenerator:

    def __init__(self, input_file="compatibility_conflicts.json", output_file="compatibility_report.json", analysis_file="compatibility_knowledge.json"):

        self.input_file = str(input_file)

        self.output_file = str(output_file)

        self.conflicts = []
        
        self.analysis_file = str(analysis_file)

        self.analysis = {}
    def load_conflicts(self):

        with open(self.input_file, "r") as f:

            data = json.load(f)

        self.conflicts = data.get(

            "conflicts",

            []

        )
        
    def load_analysis(self):

        with open(self.analysis_file) as f:

            self.analysis = json.load(f)
        
    def generate_summary(self):

        summary = {

            "Synchronization": 0,

            "Consistency": 0,

            "Reachability": 0,

            "Deadlock": 0

        }

        for conflict in self.conflicts:

            category = conflict["category"]

            if category in summary:

                summary[category] += 1

        return summary

    def determine_status(self):

        if len(self.conflicts) > 0:
            return "Incompatible"

        transitions = self.analysis["transition_analysis"]

        if any(t["requires_merge"] for t in transitions):
            return "Compatible with Merged Guards"

        return "Compatible"
    
    def determine_verdict(self):

        if len(self.conflicts) == 0:

            return (
                "All synchronization, consistency, reachability and deadlock "
                "verification properties were successfully satisfied. "
                "The interacting smart contracts preserve their intended behaviour."
            )

        return (
            "Compatibility verification identified one or more conflicts "
            "that prevent safe composition of the interacting smart contracts."
        )
    def analyze_root_cause(self, summary):

        if summary["Consistency"] > 0:

            return (

                "The verification results indicate that the primary "
                "compatibility issue originates from conflicting business "
                "rules between the interacting smart contracts. "
                "These semantic inconsistencies subsequently propagate "
                "into workflow synchronization, reachability, and "
                "completion failures."

            )

        elif summary["Synchronization"] > 0:

            return (

                "The primary compatibility issue arises from workflow "
                "synchronization mismatches between the interacting contracts."

            )

        elif summary["Reachability"] > 0:

            return (

                "The interacting contracts cannot jointly reach their "
                "intended completion state."

            )

        elif summary["Deadlock"] > 0:

            return (

                "The interacting contracts contain execution paths that "
                "prevent guaranteed completion."

            )

        return (
            "Verification confirmed that the interacting smart contracts "
            "preserve synchronized workflow behaviour under the synthesized "
            "merged guards. No behavioural incompatibilities were detected."
        )
    def aggregate_recommendations(self):

        recommendations = []

        categories = {

            conflict["category"]

            for conflict in self.conflicts

        }

        if "Consistency" in categories:

            recommendations.append(

                "Review and harmonize conflicting business rules across the interacting smart contracts."

            )

        if "Synchronization" in categories:

            recommendations.append(

                "Align workflow mappings and synchronization points between both contracts."

            )

        if "Reachability" in categories:

            recommendations.append(

                "Revise workflow constraints to ensure successful completion states remain reachable."

            )

        if "Deadlock" in categories:

            recommendations.append(

                "Modify blocking transitions or introduce recovery paths to eliminate execution deadlocks."

            )

        if not recommendations:

            recommendations.append(

                "No corrective actions are required."

            )

        return recommendations
    
    def generate_report(self):
        
        summary = self.generate_summary()

        status=self.determine_status()

        verdict = self.determine_verdict()

        failed_rules = [
            conflict["rule_id"]
            for conflict in self.conflicts
        ]

        report = CompatibilityReport(

        compatibility_status=status,

        total_conflicts=len(self.conflicts),

        summary=summary,

        overall_verdict=verdict,

        primary_root_cause=self.analyze_root_cause(summary),

        warnings=self.generate_warnings(),

        milestone_observations=self.generate_milestone_observations(),

        recommendations=self.aggregate_recommendations(),

        failed_rules=failed_rules

        )

        

        return report

    def generate_warnings(self):

        warnings = []

        transitions = self.analysis["transition_analysis"]

        merged = [
            t for t in transitions
            if t["requires_merge"]
        ]

        if merged:

            warnings.append(
                "Compatibility was established using synthesized merged guards."
            )

            warnings.append(
                "Manual validation of the synthesized business rules is recommended before deployment."
            )

        return warnings

    def generate_milestone_observations(self):

        return self.analysis.get(
            "milestone_observations",
            []
        )

    def save_output(self, report):

        with open(self.output_file, "w") as f:

            json.dump(

                asdict(report),

                f,

                indent=4

            )

        print(

            f"\nCompatibility report saved to {self.output_file}"

        )
    def run(self):

        self.load_conflicts()
        self.load_analysis()
        report = self.generate_report()

        self.save_output(report)



def main():

    generator = CompatibilityReportGenerator()

    generator.run()


if __name__ == "__main__":

    main()
