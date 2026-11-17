import json
import re
from collections import defaultdict


OPERATOR_MAP = {
    "equal": "=",
    "not_equal": "!=",
    "greater": ">",
    "greater_equal": ">=",
    "less": "<",
    "less_equal": "<="
}

# HELPERS

def load_json(path):

    with open(path, "r") as f:
        return json.load(f)


def save_model(lines, path):

    with open(path, "w") as f:

        f.write(
            "\n".join(
                line.rstrip()
                for line in lines
            )
        )


def sanitize_state_name(state):

    if state is None:
        return None

    state = str(state)

    state = state.replace("(", "")
    state = state.replace(")", "")
    state = state.replace("'", "")
    state = state.replace(" ", "")
    state = state.replace(",", "_")

    return state


def sanitize_identifier(name):

    return re.sub(r'[^A-Za-z0-9_]', '_', str(name))



# VARIABLE DISCOVERY


def discover_variables(composed_model):

    aliases = {}

    declarations = {}

    mapping = composed_model.get("variable_mapping")

    if mapping is None:
        return aliases, declarations

    for variable in mapping["variables"]:

        canonical = variable["fsm1_variable"]

        aliases[variable["fsm1_variable"]] = canonical
        aliases[variable["fsm2_variable"]] = canonical

        datatype = variable["type"]

        if datatype == "integer":

            declarations[canonical] = "0..100"

        elif datatype == "boolean":

            declarations[canonical] = "boolean"

    return aliases, declarations



# GUARD TRANSLATION


def guard_to_nusmv(guard, aliases=None):

    if guard is None:
        return None

    variable = guard.get("variable")

    if variable:

        if aliases:
            variable = aliases.get(variable, variable)

    operator = guard["operator"]

    if operator == "between":

        return (
            f"({variable} >= {guard['min']} & "
            f"{variable} <= {guard['max']})"
        )

    if operator == "outside":

        return (
            f"({variable} < {guard['min']} | "
            f"{variable} > {guard['max']})"
        )

    if operator in OPERATOR_MAP:

        symbol = OPERATOR_MAP[operator]

        return (
            f"({variable} {symbol} "
            f"{guard['value']})"
        )

    raise ValueError(
        f"Unsupported guard operator: {operator}"
    )



# TRANSITION ORGANIZATION

def group_transitions(transitions):

    transition_map = defaultdict(list)

    for transition in transitions:

        source = sanitize_state_name(
            transition["from"]
        )

        transition_map[source].append(
            transition
        )

    return transition_map


# STATE DICTIONARY

def build_state_dictionary(composed_model):

    state_dictionary = {}

    if "state_dictionary" in composed_model:

        raw = composed_model["state_dictionary"]

        if raw and isinstance(
            next(iter(raw.values())),
            list
        ):
            return raw

        flat = {}

        for _, contract_states in raw.items():

            for proposition, states in contract_states.items():

                flat.setdefault(
                    proposition,
                    []
                )

                for state in states:

                    if state not in flat[proposition]:

                        flat[proposition].append(
                            state
                        )

        return flat

    for state in composed_model["states"]:

        clean = sanitize_state_name(state)

        matches = re.findall(
            r"'([^']+)'",
            state
        )

        if len(matches) != 2:
            continue

        fsm1_state, fsm2_state = matches

        state_dictionary.setdefault(
            fsm1_state,
            []
        ).append(clean)

        state_dictionary.setdefault(
            fsm2_state,
            []
        ).append(clean)

    return state_dictionary


def generate_define_section(state_dictionary):

    lines = []

    lines.append("\nDEFINE\n\n")

    for proposition in sorted(state_dictionary.keys()):

        expression = " |\n        ".join(

            f"global_state = {sanitize_state_name(state)}"

            for state in state_dictionary[proposition]

        )

        lines.append(

            f"    {sanitize_identifier(proposition)} :=\n"

            f"        {expression};\n\n"

        )

    return lines

# MERGED GUARD LOOKUP

def build_guard_lookup(
    verification_rules
):
    

    lookup = {}

    for rule in verification_rules[
        "consistency_rules"
    ]:

        lookup[
            rule["transition_id"]
        ] = {

            "requires_merge": True,

            "merged_guard":
                rule["merged_guard"]

        }

    return lookup

# TRANSITION GUARD

def get_transition_guard(
    transition,
    guard_lookup
):
   
    transition_id = transition.get("id")

    lookup = guard_lookup.get(
        transition_id,
        {}
    )

    if lookup.get("requires_merge"):

        return lookup.get(
            "merged_guard"
        )

    return transition[
        "fsm1_transition"
    ].get(
        "guard"
    )
    


def generate_module():

    return [

        "MODULE main\n\n"

    ]


def generate_var_section(composed_model):
    
    aliases, declarations = discover_variables(
        composed_model
    )
    lines = []

    lines.append("VAR\n\n")

    lines.append(

        "    global_state : {\n"

    )

    states = [

        sanitize_state_name(s)

        for s in composed_model["states"]

    ]

    for i, state in enumerate(states):

        if i < len(states) - 1:

            lines.append(

                f"        {state},\n"

            )

        else:

            lines.append(

                f"        {state}\n"

            )

    lines.append(

        "    };\n\n"

    )

    for variable, domain in declarations.items():

        lines.append(

            f"    {variable} : {domain};\n"

        )

    lines.append("\n")

    return lines


def generate_assign_header(composed_model):

    lines = []

    lines.append(

        "ASSIGN\n\n"

    )

    initial_state = sanitize_state_name(

        composed_model["initial_state"]

    )

    lines.append(

        f"    init(global_state) := {initial_state};\n\n"

    )

    return lines

def generate_variable_initialization(composed_model):

    aliases, declarations = discover_variables(
        composed_model
    )

    lines = []

    for variable in declarations:

        lines.append(

            f"    next({variable}) := {variable};\n"

        )

    lines.append("\n")

    return lines

def generate_transition_section(
    composed_model,
    guard_lookup
):

    lines = []
    lines.append(
        "    next(global_state) := case\n"
    )
    grouped = group_transitions(
        composed_model["transitions"]
    )

    for source_state, transitions in grouped.items():

        lines.append("\n")

        for transition in transitions:

            target_state = sanitize_state_name(
                transition["to"]
            )

            guard = get_transition_guard(
                transition,
                guard_lookup
            )

            if guard:

                guard_expression = guard_to_nusmv(
                    guard
                )

                condition = (
                    f"global_state = "
                    f"{sanitize_state_name(source_state)} "
                    f"& ({guard_expression})"
                )

            else:

                condition = (
                    f"global_state = "
                    f"{sanitize_state_name(source_state)}"
                )

            lines.append(
                f"        {condition} : "
                f"{target_state};\n"
            )

    lines.append("\n")
    lines.append(
        "        TRUE : global_state;\n"
    )
    lines.append(
        "    esac;\n"
    )

    return lines


def append_specifications(
    lines,
    verification_rules
):

    lines.append("")
    lines.append("-- ======================================")
    lines.append("-- Verification Properties")
    lines.append("-- ======================================")
    lines.append("")

    lines.append("-- Synchronization\n")
    lines.append("\n")
    for rule in verification_rules["synchronization_rules"]:

        source = sanitize_state_name(rule["source"])
        target = sanitize_state_name(rule["target"])

        lines.append(f"-- {rule['rule_id']}\n")

        if rule["transition_type"] == "workflow":

            lines.append(
                f"CTLSPEC AG(global_state = {source} -> AF(global_state = {target}));\n"
            )

        elif (
            rule["transition_type"] == "decision"
            and rule["requires_merge"]
            and rule["merged_guard"] is not None
        ):

            guard = guard_to_nusmv(rule["merged_guard"])

            lines.append(
                f"CTLSPEC AG((global_state = {source} & {guard}) -> AF(global_state = {target}));\n"
            )

        else:

            lines.append(
                f"CTLSPEC AG(global_state = {source} -> AF(global_state = {target}));\n"
            )

        lines.append("\n")


    lines.append("-- Consistency\n")
    lines.append("")

    for rule in verification_rules["consistency_rules"]:

        target = sanitize_state_name(
            rule["target"]
        )

        guard = guard_to_nusmv(
            rule["merged_guard"]
        )

        lines.append(
            f"-- {rule['rule_id']}\n"
        )

        source = sanitize_state_name(rule["source"])

        lines.append(
            f"CTLSPEC AG((global_state = {source} & {guard}) -> AX(global_state = {target}));\n"
        )

        lines.append("\n")


    lines.append("-- Reachability \n ")
    lines.append("")

    targets = []

    for rule in verification_rules["reachability_rules"]:

        targets.append(
            f"global_state = {sanitize_state_name(rule['target_state'])}"
        )

    terminal_expression = " | ".join(targets)

    lines.append("-- REACH_TERMINAL\n")

    lines.append(
        f"CTLSPEC AG(EF({terminal_expression}));\n"
    )

    lines.append("\n")


    lines.append("-- Deadlock\n ")
    lines.append("")

    lines.append(
        "-- DEADLOCK_SUCCESSOR\n"
    )

    lines.append(
        "CTLSPEC AG(EX TRUE);\n"
    )

    lines.append("\n")

    terminal_states = []

    for state in verification_rules[
        "deadlock_rules"
    ][1]["terminal_states"]:

        terminal_states.append(
            f"global_state = {sanitize_state_name(state)}"
        )

    terminal_expression = " | ".join(
        terminal_states
    )

    lines.append(
        "-- DEADLOCK_TERMINAL\n"
    )

    lines.append(
        f"CTLSPEC AG(EF({terminal_expression}));\n"
    )

    lines.append("\n")


def main():

    composed_model = load_json(
        "composed_fsmeg1.json"
    )

    verification_rules = load_json(
        "verification_ruleseg1.json"
    )
    state_dictionary = build_state_dictionary(
    composed_model
    )


    guard_lookup = build_guard_lookup(
        verification_rules
    )

    smv_lines = generate_module()
    
    smv_lines.extend(
        generate_var_section(
            composed_model
        )
    )

    smv_lines.extend(
        generate_define_section(
            state_dictionary
        )
    )

    smv_lines.extend(
        generate_assign_header(composed_model)
    )

    smv_lines.extend(
        generate_variable_initialization(
            composed_model
        )
    )

    smv_lines.extend(
        generate_transition_section(
            composed_model,
            guard_lookup
        )
    )

    append_specifications(
        smv_lines,
        verification_rules
    )

    save_model(
        smv_lines,
        "verification_modeleg1.smv"
    )

    print(
        "\nVerification model written to verification_modeleg1.smv"
    )


if __name__ == "__main__":

    main()
