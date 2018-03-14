"""
Example of a multi-lane network with human-driven vehicles.
"""
from flow.core.params import SumoParams, EnvParams, NetParams, InitialConfig, \
    InFlows
from flow.core.vehicles import Vehicles
from flow.core.traffic_lights import TrafficLights

from flow.scenarios.bridge_toll.gen import BBTollGenerator
from flow.scenarios.bridge_toll.scenario import BBTollScenario
from flow.controllers.lane_change_controllers import *
from flow.controllers.velocity_controllers import FollowerStopper
from flow.controllers.car_following_models import SumoCarFollowingController
from flow.controllers.routing_controllers import ContinuousRouter
from flow.core.params import SumoCarFollowingParams
from flow.core.params import SumoLaneChangeParams
from flow.envs.bottleneck_env import BottleNeckEnv
from flow.core.experiment import SumoExperiment

import numpy as np

def bottleneck(sumo_binary=None):

    SCALING = 4
    NUM_LANES = 4*SCALING  # number of lanes in the widest highway
    DISABLE_TB = True
    DISABLE_RAMP_METER = True

    if sumo_binary is None:
        sumo_binary = "sumo-gui"
    sumo_params = SumoParams(sim_step = 0.5, sumo_binary="sumo-gui", overtake_right=False)

    vehicles = Vehicles()

    vehicles.add(veh_id="human",
                 speed_mode=31,
                 lane_change_controller=(SumoLaneChangeController, {}),
                 acceleration_controller=(SumoCarFollowingController, {}),
                 # routing_controller=(ContinuousRouter, {}),
                 lane_change_mode=0b100000101,
                 sumo_lc_params=SumoLaneChangeParams(lcKeepRight=0),
                 num_vehicles=5)

    vehicles.add(veh_id="followerstopper",
                 speed_mode=31,
                 lane_change_controller=(SumoLaneChangeController, {}),
                 acceleration_controller=(FollowerStopper, {"v_des":5}),
                 routing_controller=(ContinuousRouter, {}),
                 lane_change_mode=0b100000101,
                 sumo_lc_params=SumoLaneChangeParams(lcKeepRight=0),
                 num_vehicles=5)

    additional_env_params = {"target_velocity": 40, "disable_tb": True,
                             "disable_ramp_metering": True}
    env_params = EnvParams(additional_params=additional_env_params,
                           lane_change_duration=1)

    # flow rate

    # MAX OF 3600 vehicles per lane per hour i.e. flow_rate <= 3600 *
    flow_rate = 2100 * SCALING
    # percentage of flow coming out of each lane
    # flow_dist = np.random.dirichlet(np.ones(NUM_LANES), size=1)[0]
    flow_dist = np.ones(NUM_LANES)/NUM_LANES

    inflow = InFlows()
    for i in range(NUM_LANES):
        lane_num = str(i)
        veh_per_hour = flow_rate * flow_dist[i]
        print(veh_per_hour)
        veh_per_second = veh_per_hour/3600
        print(veh_per_second)
        inflow.add(veh_type="human", edge="1", probability=veh_per_second*0.75,#vehsPerHour=veh_per_hour *0.8,
                   departLane=lane_num, departSpeed=23)
        inflow.add(veh_type="followerstopper", edge="1", probability=veh_per_second*0.25,#vehsPerHour=veh_per_hour * 0.2,
                   departLane=lane_num, departSpeed=23)

    traffic_lights = TrafficLights()
    if not DISABLE_TB:
        traffic_lights.add(node_id="2")
    if not DISABLE_RAMP_METER:
        traffic_lights.add(node_id="3")

    additional_net_params = {"scaling": SCALING}
    net_params = NetParams(in_flows=inflow,
                           no_internal_links=False, additional_params=additional_net_params)

    initial_config = InitialConfig(spacing="random", min_gap=5,
                                   lanes_distribution=float("inf"),
                                   edges_distribution=["2", "3", "4", "5"])

    scenario = BBTollScenario(name="bay_bridge_toll",
                              generator_class=BBTollGenerator,
                              vehicles=vehicles,
                              net_params=net_params,
                              initial_config=initial_config,
                              traffic_lights=traffic_lights)

    env = BottleNeckEnv(env_params, sumo_params, scenario)

    return SumoExperiment(env, scenario)


if __name__ == "__main__":
    # import the experiment variable
    exp = bottleneck(sumo_binary="sumo-gui")

    # run for a set number of rollouts / time steps
    exp.run(10, 500)