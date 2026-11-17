import json
from collections import deque

class FSM:

    def __init__(self, data):

        self.name = data["name"]

        self.variables = data.get("variables", {})

        self.initial_state = data["initial_state"]

        self.states = set(data["states"])

        self.transition_map = {}

        for transition in data["transitions"]:

            src = transition["from"]

            if src not in self.transition_map:
                self.transition_map[src] = []

            self.transition_map[src].append(transition)

    def get_transitions(self, state):

        return self.transition_map.get(state, [])



# LOADERS

def load_fsm(path):

    with open(path, "r") as f:
        return FSM(json.load(f))


def load_interaction_mapping(path):

    with open(path, "r") as f:
        data = json.load(f)

    fsm1_levels = {}
    fsm2_levels = {}

    allowed_pairs = set()

    for mapping in data["interactions"]:

        level = mapping["level"]

        state1 = mapping["fsm1_state"]
        state2 = mapping["fsm2_state"]

        fsm1_levels[state1] = level
        fsm2_levels[state2] = level

        allowed_pairs.add((state1, state2))

    return {

        "fsm1": fsm1_levels,

        "fsm2": fsm2_levels,

        "allowed_pairs": allowed_pairs
    }

def load_variable_mapping(path):

    with open(path, "r") as f:
        return json.load(f)


# MILESTONE LOOKUP


def build_milestone_lookup(interaction_map):
    """
    Builds lookup tables directly from the interaction mapping.

    Only explicitly declared interaction pairs are considered valid.
    """

    fsm1_to_fsm2 = {}

    fsm2_to_fsm1 = {}

    for state1, state2 in interaction_map["allowed_pairs"]:

        fsm1_to_fsm2[state1] = state2

        fsm2_to_fsm1[state2] = state1

    return (
        interaction_map["allowed_pairs"],
        fsm1_to_fsm2,
        fsm2_to_fsm1
    )

# NEXT MILESTONE SEARCH

def find_next_milestones(fsm, current_state, interaction_states):
    """
    Returns the unique next interaction milestones reachable
    from the current interaction state.

    Internal states are skipped.

    Multiple internal paths leading to the same interaction
    milestone are collapsed into one transition.
    """

    queue = deque()

    visited = set()

    queue.append((current_state, None, []))

    milestones = {}

    while queue:

        state, inherited_guard,path = queue.popleft()

        if state in visited:
            continue

        visited.add(state)

        for transition in fsm.get_transitions(state):

            next_state = transition["to"]

            guard = transition.get("guard")

            effective_guard = (
                guard if guard is not None else inherited_guard
            )

            if next_state in interaction_states:

                if next_state not in milestones:

                    milestones[next_state] = {

                        "state": next_state,

                        "guard": effective_guard,

                        "intermediate_states": path.copy()

                    }

            else:

                queue.append(

                    (
                        next_state,
                        effective_guard,
                        path + [next_state]
                    )

                )

    return list(milestones.values())

# STATE DICTIONARY GENERATION

def generate_state_dictionary(states, fsm1_name, fsm2_name):

    state_dict = {
        fsm1_name: {},
        fsm2_name: {}
    }

    for state_a, state_b in states:

        global_state = f"{state_a}_{state_b}"

        # FSM 1 propositions
        if state_a not in state_dict[fsm1_name]:
            state_dict[fsm1_name][state_a] = []

        state_dict[fsm1_name][state_a].append(global_state)

        # FSM 2 propositions
        if state_b not in state_dict[fsm2_name]:
            state_dict[fsm2_name][state_b] = []

        state_dict[fsm2_name][state_b].append(global_state)

    return state_dict


# MILESTONE-BASED COMPOSITION

def compose_fsms(
        fsm1,
        fsm2,
        interaction_map,
        variable_map):

    
    # Build milestone lookup tables

    allowed_pairs, fsm1_to_fsm2, fsm2_to_fsm1 = \
    build_milestone_lookup(interaction_map)

    interaction_states_fsm1 = set(fsm1_to_fsm2.keys())
    interaction_states_fsm2 = set(fsm2_to_fsm1.keys())

    # Initial composed state

    initial = (
        fsm1.initial_state,
        fsm2.initial_state
    )

    queue = deque([initial])

    visited = set()
    visited.add(initial)

    composed_transitions = []
    transition_counter = 1
    
    #BFS

    while queue:

        current = queue.popleft()

        state_a, state_b = current

       
        # Find next interaction milestones
 

        next_a = find_next_milestones(
            fsm1,
            state_a,
            interaction_states_fsm1
        )

        next_b = find_next_milestones(
            fsm2,
            state_b,
            interaction_states_fsm2
        )
       

        # Terminal milestone handling
       

        # Both workflows reached terminal interaction milestones.
        #  No outgoing composed transitions.
        if not next_a and not next_b:
            continue

        # One workflow terminated before the other.
        # Shows incompatible workflow structure.
        if not next_a or not next_b:
            continue
        
        # Compose milestone transitions

        for transition_a in next_a:

            for transition_b in next_b:

                pair = (
                    transition_a["state"],
                    transition_b["state"]
                )

                # Only compose mapped milestone pairs
                if pair not in allowed_pairs:
                    continue

                next_global = pair

                transition_id = f"T{transition_counter}"

                composed_transitions.append({

                    "id": transition_id,

                    "from": current,

                    "to": next_global,

                    "fsm1_transition": {

                        "from": state_a,

                        "to": transition_a["state"],

                        "guard": transition_a["guard"]

                    },

                    "fsm2_transition": {

                        "from": state_b,

                        "to": transition_b["state"],

                        "guard": transition_b["guard"]

                    },
                    "fsm1_intermediate_states":
                        transition_a["intermediate_states"],

                    "fsm2_intermediate_states":
                        transition_b["intermediate_states"]

                })
                transition_counter+=1

                if next_global not in visited:

                    visited.add(next_global)

                    queue.append(next_global)


    state_dictionary = generate_state_dictionary(

        visited,

        fsm1.name,

        fsm2.name

    )

    return {

        "initial_state": initial,

        "states": list(visited),

        "transitions": composed_transitions,

        "variable_mapping": variable_map,

        "state_dictionary": state_dictionary

    }


def save_model(model, filename):

    output = {

        "initial_state": str(
            model["initial_state"]
        ),

        "states": [
            str(s)
            for s in model["states"]
        ],

        "transitions": [

           {
            "id": t["id"],

            "from": str(t["from"]),

            "to": str(t["to"]),

            "fsm1_transition": t["fsm1_transition"],

            "fsm2_transition": t["fsm2_transition"],

            "fsm1_intermediate_states":
                t["fsm1_intermediate_states"],

            "fsm2_intermediate_states":
                t["fsm2_intermediate_states"]
        }

            for t in model["transitions"]

        ],

        "variable_mapping":
        model["variable_mapping"],

        "state_dictionary":
        model["state_dictionary"]
    }

    with open(filename, "w") as f:

        json.dump(
            output,
            f,
            indent=4
        )



if __name__ == "__main__":

    fsm1 = load_fsm("fsm_alpha10.json")

    fsm2 = load_fsm("fsm_beta10.json")

    interaction_map = load_interaction_mapping(
        "interaction_mapping.json"
    )

    variable_map = load_variable_mapping(
        "variable_mapping.json"
    )

    composed_model = compose_fsms(
        fsm1,
        fsm2,
        interaction_map,
        variable_map
    )

    print(
        "\nStates:",
        len(composed_model["states"])
    )

    print(
        "Transitions:",
        len(composed_model["transitions"])
    )

    save_model(
        composed_model,
        "composed_fsmeg1.json"
    )

    print(
        "\nSaved to composed_fsmeg1.json"
    )

