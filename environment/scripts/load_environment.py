#!/usr/bin/env python

# Modified from RethinkRobotics website

import argparse
import struct
import sys
import copy
import rospy
import rospkg

from gazebo_msgs.srv import (
    SpawnModel,
    DeleteModel,
    GetModelState,
    GetLinkState,
)
from gazebo_msgs.msg import (
    LinkState,
)
from geometry_msgs.msg import (
    PoseStamped,
    Pose,
    Point,
    Quaternion,
)
from std_msgs.msg import (
    Header,
    Empty,
    Bool,
)

import tf
from tf.transformations import *

from environment.srv import * 
from agent.srv import MoveToStartSrv

environment = 'default'

pub_all = rospy.Publisher('models_loaded', Bool, queue_size=10)
moveToStartProxy = rospy.ServiceProxy('move_to_start_srv', MoveToStartSrv)
    
#SPAWN WALL AT 1.1525 z to be above table or 0.3755 to be below
def load_gazebo_models(env='default'):

    table_pose=Pose(position=Point(x=0.78, y=0.0, z=0.0))
    block_pose=Pose(position=Point(x=0.8, y=0.0185, z=0.8))
    right_button_pose=Pose(position=Point(x=0.525, y=-0.2715, z=0.8))
    left_button_pose=Pose(position=Point(x=0.525, y=0.1515, z=0.8))
    block_reference_frame="world"
    cup_pose=Pose(position=Point(x=0.5, y=0.0, z=0.8))
    marble_pose=Pose(position=Point(x=0.5, y=0.0, z=0.9))
    cover_pose=Pose(position=Point(x=0.5, y=0.0, z=0.9))
    reference_frame="world"


    # Get Models' Path
    model_path = rospkg.RosPack().get_path('environment')+"/models/"

    table_xml = ''
    cup_xml = ''
    marbleB_xml = ''
    marbleR_xml = ''


    moveToStartProxy('both')

    with open (model_path + "cafe_table/model.sdf", "r") as table_file:
        table_xml=table_file.read().replace('\n', '')



    ###############################
    ############ HEAVY ############
    if env == 'heavy': 
        with open (model_path + "cup_with_cover/cup_model_heavy.sdf", "r") as cup_file:
            cup_xml=cup_file.read().replace('\n', '')
        with open (model_path + "cup_with_cover/cover_model.sdf", "r") as cover_file:
            cover_xml=cover_file.read().replace('\n', '')

    ###############################
    ######## HIGH FRICTION ########
    elif env == 'high_friction':
        with open (model_path + "cup_with_cover/cup_model_high_friction.sdf", "r") as cup_file:
            cup_xml=cup_file.read().replace('\n', '')
        with open (model_path + "cup_with_cover/cover_model_high_friction.sdf", "r") as cover_file:
            cover_xml=cover_file.read().replace('\n', '')


    ###############################
    ######## HEAVY HIGH FRICTION ##
    elif env == 'HH':
        with open (model_path + "cup_with_cover/cup_model_heavy.sdf", "r") as cup_file:
            cup_xml=cup_file.read().replace('\n', '')
        with open (model_path + "cup_with_cover/cover_model_heavy_high_friction.sdf", "r") as cover_file:
            cover_xml=cover_file.read().replace('\n', '')


    ###############################
    ########### DEFAULT ########### 
    else:
        with open (model_path + "plastic_cup/model.sdf", "r") as cup_file:
            cup_xml=cup_file.read().replace('\n', '')
        with open (model_path + "marble/modelB.sdf", "r") as marble_file:
            marbleB_xml=marble_file.read().replace('\n', '')
        with open (model_path + "marble/modelR.sdf", "r") as marble_file:
            marbleR_xml=marble_file.read().replace('\n', '')

    # Spawn Table SDF and other URDFs
    rospy.wait_for_service('/gazebo/spawn_sdf_model')
    spawn_sdf = rospy.ServiceProxy('/gazebo/spawn_sdf_model', SpawnModel)

    try:
        spawn_sdf = rospy.ServiceProxy('/gazebo/spawn_sdf_model', SpawnModel)
        resp_sdf = spawn_sdf("cafe_table", table_xml, "/",
                             table_pose, reference_frame)
    except rospy.ServiceException as e:
        rospy.logerr("Spawn SDF service call failed: {0}".format(e))

    try:
        spawn_sdf = rospy.ServiceProxy('/gazebo/spawn_sdf_model', SpawnModel)
        resp_sdf = spawn_sdf("plastic_cup", cup_xml, "/",
                                cup_pose, reference_frame)
    except rospy.ServiceException as e:
        rospy.logerr("Spawn URDF service call failed: {0}".format(e))
        
    try:
        num_marbles = 5
        for i in range(num_marbles):
            resp_sdf = spawn_sdf("marbleB_"+ str(i), marbleB_xml, "/",
                                marble_pose, reference_frame)
    except rospy.ServiceException as e:
        spawn_sdf("cafe_table", table_xml, "/", table_pose, reference_frame)
        spawn_sdf("cup", cup_xml, "/", cup_pose, reference_frame)
        spawn_sdf("cover", cover_xml, "/", cover_pose, reference_frame)
        # spawn_sdf("cover2", cover_xml, "/", left_button_pose, reference_frame)
        # spawn_sdf("cover3", cover_xml, "/", right_button_pose, reference_frame)

    except rospy.ServiceException as e:
        rospy.logerr("Spawn URDF service call failed: {0}".format(e))
        

    pub_all.publish(True)


def delete_gazebo_models():
    # This will be called on ROS Exit, deleting Gazebo models
    # Do not wait for the Gazebo Delete Model service, since
    # Gazebo should already be running. If the service is not
    # available since Gazebo has been killed, it is fine to error out
    num_marbles = 5
    try:
        rospy.wait_for_service('/gazebo/delete_model', timeout=60)
        pub_all.publish(False)
        
        delete_model = rospy.ServiceProxy('/gazebo/delete_model', DeleteModel)
        delete_model("cafe_table")
        delete_model("cup")
        delete_model("cover")

    except rospy.ServiceException as e:
        rospy.loginfo("Delete Model service call failed: {0}".format(e))


def handle_environment_request(req):
    action = req.action
    environment = 'default' if req.environment_setting == None else req.environment_setting
    if action == "init":
        try:
            load_gazebo_models(environment)
            return HandleEnvironmentSrvResponse(1)
        except rospy.ServiceException as e:
            rospy.logerr("Init environment call failed: {0}".format(e))
            return HandleEnvironmentSrvResponse(0)

    elif action == 'destroy':
        try:
            delete_gazebo_models()
            return HandleEnvironmentSrvResponse(1)
        except rospy.ServiceException as e:
            rospy.logerr("Destroy environment call failed: {0}".format(e))
            return HandleEnvironmentSrvResponse(0)

    elif action == 'restart':
        try:
            delete_gazebo_models()
            rospy.sleep(3)
            load_gazebo_models(environment)
            rospy.sleep(5)
            return HandleEnvironmentSrvResponse(1)

        except rospy.ServiceException as e:
            rospy.logerr("Destroy environment call failed: {0}".format(e))
            return HandleEnvironmentSrvResponse(0)
    else:
        print('No Action')


def main():

    rospy.init_node("load_environment_node")
    rospy.on_shutdown(delete_gazebo_models)
    rospy.wait_for_service('move_to_start_srv', timeout=60)
    
    s = rospy.Service("load_environment", HandleEnvironmentSrv, handle_environment_request)
    load_gazebo_models()

    rospy.spin()
    return 0

if __name__ == '__main__':
    sys.exit(main())

