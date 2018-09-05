"""Ring road example.

Trains a single autonomous vehicle to stabilize the flow of 21 human-driven
vehicles in a variable length ring road.
"""

import json

import ray
import ray.rllib.agents.ars as ars
from ray.tune import run_experiments
from ray.tune.registry import register_env

from flow.utils.registry import make_create_env
from flow.utils.rllib import FlowParamsEncoder
from flow.core.params import SumoParams, EnvParams, InitialConfig, NetParams
from flow.core.vehicles import Vehicles
from flow.controllers import RLController, IDMController, ContinuousRouter

# time horizon of a single rollout
HORIZON = 600
# number of rollouts per training iteration
N_ROLLOUTS = 36
# number of parallel workers
N_CPUS = 36

# We place one autonomous vehicle and 22 human-driven vehicles in the network
vehicles = Vehicles()
vehicles.add(
    veh_id="human",
    acceleration_controller=(IDMController, {
        "noise": 0.01
    }),
    routing_controller=(ContinuousRouter, {}),
    num_vehicles=21)
vehicles.add(
    veh_id="rl",
    acceleration_controller=(RLController, {}),
    routing_controller=(ContinuousRouter, {}),
    num_vehicles=1)

flow_params = dict(
    # name of the experiment
    exp_tag="stabilizing_the_ring",

    # name of the flow environment the experiment is running on
    env_name="WaveAttenuationPOEnv",

    # name of the scenario class the experiment is running on
    scenario="LoopScenario",

    # name of the generator used to create/modify network configuration files
    generator="CircleGenerator",

    # sumo-related parameters (see flow.core.params.SumoParams)
    sumo=SumoParams(
        sim_step=0.3,
        sumo_binary="sumo",
    ),

    # environment related parameters (see flow.core.params.EnvParams)
    env=EnvParams(
        horizon=HORIZON,
        warmup_steps=0,
        additional_params={
            "max_accel": 1,
            "max_decel": 1,
            "ring_length": [220, 222],
        },
    ),

    # network-related parameters (see flow.core.params.NetParams and the
    # scenario's documentation or ADDITIONAL_NET_PARAMS component)
    net=NetParams(
        additional_params={
            "length": 260,
            "lanes": 1,
            "speed_limit": 30,
            "resolution": 40,
        }, ),

    # vehicles to be placed in the network at the start of a rollout (see
    # flow.core.vehicles.Vehicles)
    veh=vehicles,

    # parameters specifying the positioning of vehicles upon initialization/
    # reset (see flow.core.params.InitialConfig)
    initial=InitialConfig(),
)

if __name__ == "__main__":
    ray.init(num_cpus=N_CPUS + 1, redirect_output=True)

    config = ars.DEFAULT_CONFIG.copy()
    config["num_workers"] = N_CPUS
    config["num_deltas"] = N_CPUS
    config["deltas_used"] = N_CPUS
    config["policy_type"] = "MLPPolicy"
    config["fcnet_hiddens"] = [4, 4]

    # save the flow params for replay
    flow_json = json.dumps(
        flow_params, cls=FlowParamsEncoder, sort_keys=True, indent=4)
    config['env_config']['flow_params'] = flow_json

    create_env, env_name = make_create_env(params=flow_params, version=0)

    # Register as rllib env
    register_env(env_name, create_env)

    trials = run_experiments({
        flow_params["exp_tag"]: {
            "run": "ARS",
            "env": env_name,
            "config": {
                **config
            },
            "checkpoint_freq": 20,
            "max_failures": 999,
            "stop": {
                "training_iteration": 500,
            },
        },
    })
