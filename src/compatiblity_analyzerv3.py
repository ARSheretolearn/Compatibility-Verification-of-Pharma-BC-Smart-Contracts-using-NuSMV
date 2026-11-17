import json

def load(path):

    with open(path, "r") as f:
        return json.load(f)


def save(data, path):

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# STATE PARSING

def parse_state(state_string):

    state_string = state_string.strip()

    state_string = (
        state_string
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
    )

    left, right = [

        s.strip()

        for s in state_string.split(",")

    ]

    return left, right


# GUARDS

def simplify_guard(guard):

    if guard is None:
        return None

    return {

        "operator": guard["operator"],

        "value": guard.get("value"),

        "min": guard.get("min"),

        "max": guard.get("max")
    }

# GUARD COMPARISON

OPPOSITE_OPERATORS = {

    ("greater_equal", "less"),
    ("less", "greater_equal"),

    ("greater", "less_equal"),
    ("less_equal", "greater"),

    ("between", "outside"),
    ("outside", "between")
}
def compare_guards(guard1, guard2):

    # Compare two transition guards.

    if guard1 is None and guard2 is None:

        return {

            "relationship": "unconstrained",

            "reason":
                "Neither transition has a decision guard.",

            "merged_guard": None

        }

    if guard1 is None or guard2 is None:

        return {

            "relationship": "compatible",

            "reason":
                "Only one transition is guarded.",

            "merged_guard":
                simplify_guard(
                    guard1 if guard1 else guard2
                )
        }

    if guard1["variable"] != guard2["variable"]:

        return {

            "relationship": "unknown",

            "reason":
                "Variable mapping required.",

            "merged_guard": None

        }

    if guard1 == guard2:

        return {

            "relationship": "identical",

            "reason":
                "Both transitions use the same guard.",

            "merged_guard":
                simplify_guard(guard1)

        }

    op1 = guard1["operator"]
    op2 = guard2["operator"]

    if "value" in guard1 and "value" in guard2:

        v1 = guard1["value"]
        v2 = guard2["value"]



        if op1 == op2:

            if op1 in ("greater", "greater_equal"):

                merged = max(v1, v2)

            elif op1 in ("less", "less_equal"):

                merged = max(v1, v2)

            else:

                merged = v1

            return {

                "relationship": "compatible_with_merge",

                "reason":
                    "Thresholds overlap.",

                "merged_guard": {

                    "variable":
                        guard1["variable"],

                    "operator": op1,

                    "value": merged
                }

            }


        if (op1, op2) in OPPOSITE_OPERATORS:

            return {

                "relationship": "incompatible",

                "reason":
                    "Opposing guard directions.",

                "merged_guard": None

            }


    return {

        "relationship": "unknown",

        "reason":
            "Unsupported guard combination.",

        "merged_guard": None

    }

# VARIABLE NORMALIZATION

def build_variable_lookup(variable_mapping):

    lookup = {}

    for mapping in variable_mapping["variables"]:

        canonical = mapping["fsm1_variable"]

        lookup[mapping["fsm1_variable"]] = canonical
        lookup[mapping["fsm2_variable"]] = canonical

    return lookup


def normalize_guard(guard, lookup):

    if guard is None:
        return None

    guard = guard.copy()

    variable = guard["variable"]

    if variable in lookup:
        guard["variable"] = lookup[variable]

    return guard


# TRANSITION ANALYSIS

def analyze_transition(transition, variable_lookup):
    """
    Analyse one composed transition.

    Returns a semantic description of the paired transitions.
    """

    t1 = transition["fsm1_transition"]
    t2 = transition["fsm2_transition"]

    guard1 = normalize_guard(
        t1["guard"],
        variable_lookup
    )

    guard2 = normalize_guard(
        t2["guard"],
        variable_lookup
    )

    comparison = compare_guards(
        guard1,
        guard2
    )

    return {

        "transition_id": transition.get("id"),

        "from": transition["from"],

        "to": transition["to"],

        "fsm1_transition": t1,

        "fsm2_transition": t2,

        "transition_type":

            "decision"
            if guard1 or guard2
            else "workflow",

        "relationship":
            comparison["relationship"],

        "requires_merge":

            comparison["merged_guard"] is not None
            and
            guard1 != guard2,

        "merged_guard":
            comparison["merged_guard"],

        "reason":
            comparison["reason"]

    }


# DECISION ANALYSIS

def transition_analysis(composed_model):
   

    variable_lookup = build_variable_lookup(
        composed_model["variable_mapping"]
    )

    analysis = []

    for transition in composed_model["transitions"]:

        result = analyze_transition(
            transition,
            variable_lookup
        )

        analysis.append(result)

    return analysis


# WORKFLOW ANALYSIS

def workflow_analysis(composed_model):
    """
    Analyse the milestone workflow represented by the
    composed FSM.
    """

    states = composed_model["states"]
    transitions = composed_model["transitions"]

    incoming = {state: 0 for state in states}
    outgoing = {state: 0 for state in states}

    for transition in transitions:

        src = transition["from"]
        dst = transition["to"]

        outgoing[src] += 1
        incoming[dst] += 1

    workflow = []

    for state in states:

        left, right = parse_state(state)

        workflow.append({

            "state": state,

            "fsm1_state": left,

            "fsm2_state": right,

            "incoming": incoming[state],

            "outgoing": outgoing[state],

            "initial": (
                state ==
                composed_model["initial_state"]
            ),

            "terminal": (
                outgoing[state] == 0
            )

        })

    return workflow


# MILESTONE OBSERVATIONS


def milestone_observations(composed_model):
    """
    Detect additional workflow states that exist between
    synchronized milestone states.
    """

    observations = []

    for transition in composed_model["transitions"]:

        extra1 = transition.get(
            "fsm1_intermediate_states",
            []
        )

        extra2 = transition.get(
            "fsm2_intermediate_states",
            []
        )

        if extra1 or extra2:

            from_state = transition["from"]
            to_state = transition["to"]

            for state in extra1:

                observations.append(
                    f"There exists an intermediate state "
                    f"'{state}' in FSM1 between "
                    f"{from_state} and {to_state}."
                )

            for state in extra2:

                observations.append(
                    f"There exists an intermediate state "
                    f"'{state}' in FSM2 between "
                    f"{from_state} and {to_state}."
                )

    return observations

# SYNCHRONIZATION ANALYSIS

def synchronization_analysis(decision_results):
    """
    Summarize synchronization quality across the composed
    milestone graph.

    Since the Composer already synchronizes the workflows,
    this stage evaluates whether each synchronized milestone
    transition is behaviorally compatible.
    """

    summary = {

        "total_transitions": len(decision_results),

        "compatible_with_merge": 0,

        "identical": 0,

        "unconstrained": 0,

        "incompatible": 0,

        "unknown": 0,

        "details": []

    }

    for result in decision_results:

        relation = result["relationship"]

        if relation in summary:

            summary[relation] += 1

        summary["details"].append({

            "from": result["from"],

            "to": result["to"],

            "relationship": relation,

            "reason": result["reason"]

        })

    if summary["incompatible"] > 0:

        summary["overall"] = "incompatible"

    elif summary["unknown"] > 0:

        summary["overall"] = "partial"

    else:

        summary["overall"] = "compatible"

    return summary

# COMPATIBILITY ASSESSMENT


def compatibility_assessment(sync_summary):


    if sync_summary["overall"] == "compatible":

        verdict = "Compatible"

        explanation = (
            "All synchronized milestone transitions are "
            "behaviorally compatible after guard merging."
        )

    elif sync_summary["overall"] == "partial":

        verdict = "Partially Compatible"

        explanation = (
            "Some synchronized transitions require "
            "manual review."
        )

    else:

        verdict = "Incompatible"

        explanation = (
            "At least one synchronized milestone transition "
            "is behaviorally incompatible."
        )

    return {

        "verdict": verdict,

        "summary": explanation,

        "merged_transitions":
            sync_summary["compatible_with_merge"],

        "identical_transitions":
            sync_summary["identical"],

        "unconstrained_transitions":
            sync_summary["unconstrained"],

        "unknown_transitions":
            sync_summary["unknown"],

        "incompatible_transitions":
            sync_summary["incompatible"]

    }

def main():

    composed = load("composed_fsmeg1.json")

    workflow = workflow_analysis(composed)

    transitions = transition_analysis(composed)

    synchronization = synchronization_analysis(transitions)

    assessment = compatibility_assessment(
        synchronization
    )

    knowledge = {

        "workflow_analysis": workflow,

        "transition_analysis": transitions,
        "milestone_observations": milestone_observations(composed),

        "synchronization_analysis": synchronization,

        "compatibility_assessment": assessment

    }

    save(

        knowledge,

        "compatibility_knowledgeeg1.json"

    )

    print(
        "Generated compatibility_knowledgeeg1.json"
    )


if __name__ == "__main__":

    main()
    
