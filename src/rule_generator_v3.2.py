import json


def load_knowledge(path):

    with open(path, "r") as f:
        return json.load(f)

# SYNCHRONIZATION RULES
def generate_synchronization_rules(knowledge):

    rules = []

    transition_analysis = knowledge["transition_analysis"]

    counter = 1

    for transition in transition_analysis:

        rules.append({

            "rule_id": f"SYNC_{counter}",

            "type": "synchronization",

            "transition_id": transition["transition_id"],

            "source": transition["from"],

            "target": transition["to"],

            "transition_type": transition["transition_type"],

            "relationship": transition["relationship"],

            "requires_merge": transition["requires_merge"],

            "merged_guard": transition["merged_guard"]

        })

        counter += 1

    return rules

# REACHABILITY RULES
def generate_reachability_rules(knowledge):

    rules = []

    workflow = knowledge["workflow_analysis"]

    counter = 1

    for state in workflow:

        if state["terminal"]:

            rules.append({

                "rule_id": f"REACH_{counter}",

                "type": "reachability",

                "target_state": state["state"],

                "fsm1_state": state["fsm1_state"],

                "fsm2_state": state["fsm2_state"]

            })

            counter += 1

    return rules


# DEADLOCK RULES

def generate_deadlock_rules(knowledge):

    rules = []

    terminal_states = [

        state["state"]

        for state in knowledge["workflow_analysis"]

        if state["terminal"]

    ]

    rules.append({

        "rule_id": "DEADLOCK_1",

        "type": "deadlock_successor",

        "description":
        "Every reachable state must have at least one successor."

    })

    rules.append({

        "rule_id": "DEADLOCK_2",

        "type": "deadlock_terminal",

        "terminal_states": terminal_states,

        "description":
        "A compatible terminal state must always remain reachable."

    })

    return rules

# CONSISTENCY RULES

def generate_consistency_rules(knowledge):

    rules = []

    counter = 1

    for transition in knowledge["transition_analysis"]:

        if transition["transition_type"] != "decision":
            continue

        if transition["relationship"] == "compatible_with_merge":

            rules.append({

                "rule_id": f"CONS_{counter}",

                "type": "guard_consistency",

                "transition_id": transition["transition_id"],

                "source": transition["from"],

                "target": transition["to"],

                "merged_guard": transition["merged_guard"],

                "description":
                "Verify that the synthesized merged guard preserves synchronized behaviour."

            })

            counter += 1

        elif transition["relationship"] == "incompatible":

            rules.append({

                "rule_id": f"CONS_{counter}",

                "type": "guard_incompatibility",

                "transition_id": transition["transition_id"],

                "source": transition["from"],

                "target": transition["to"],

                "description":
                "Verify that incompatible decision logic prevents synchronization."

            })

            counter += 1

    return rules



def build_rule_set(knowledge):

    synchronization_rules = generate_synchronization_rules(
        knowledge
    )

    consistency_rules = generate_consistency_rules(
        knowledge
    )

    reachability_rules = generate_reachability_rules(
        knowledge
    )

    deadlock_rules = generate_deadlock_rules(
        knowledge
    )

    all_rules = (
        synchronization_rules +
        consistency_rules +
        reachability_rules +
        deadlock_rules
    )

    return {
        "metadata": {

        "generated_from":
            "compatibility_knowledge",

        "version":
            "3.0"

    },

        "synchronization_rules": synchronization_rules,

        "consistency_rules": consistency_rules,

        "reachability_rules": reachability_rules,

        "deadlock_rules": deadlock_rules,

        "statistics": {

            "total_rules": len(all_rules),

            "synchronization_rules":
                len(synchronization_rules),

            "consistency_rules":
                len(consistency_rules),

            "reachability_rules":
                len(reachability_rules),

            "deadlock_rules":
                len(deadlock_rules)

        }

    }



def write_rules(rule_set, output_path):

    with open(output_path, "w") as f:

        json.dump(
            rule_set,
            f,
            indent=4
        )

    print(
        f"\nVerification rules written to {output_path}"
    )


def main():

    knowledge = load_knowledge(
        "compatibility_knowledgeeg1.json"
    )

    rule_set = build_rule_set(
        knowledge
    )

    write_rules(
        rule_set,
        "verification_ruleseg1.json"
    )


if __name__ == "__main__":

    main()
