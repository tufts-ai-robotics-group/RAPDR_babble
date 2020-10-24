#!/usr/bin/env python

import argparse
import struct
import sys
import copy
import numpy as np

import rospy
import rospkg

from gazebo_msgs.srv import (
    SpawnModel,
    DeleteModel,
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
)


from agent.srv import *
from pddl.srv import *
from pddl.msg import *
from environment.srv import ObjectLocationSrv
from util.physical_agent import PhysicalAgent
from util.action_request import ActionRequest
from util.data_conversion import arg_list_to_hash

pa = None
obj_location_srv = rospy.ServiceProxy('object_location_srv', ObjectLocationSrv)
actionInfoProxy = rospy.ServiceProxy('get_KB_action_info_srv', GetKBActionInfoSrv)

def getObjectPose(object_name, pose_only=False):
    loc_pStamped = obj_location_srv(object_name)
    if pose_only == True:
        return loc_pStamped.location.pose
    return loc_pStamped.location

def getCorrectAction(action_name):
    action = action_name.split('_')[0]
    actions = {'push' : push,
               'grasp' : grasp, 
               'shake' : shake,
               'press' : press, 
               'drop' : drop}
    return actions[action]

################################################################################
################################################################################

#### PUSH ######################################################################
def push(req):
    objPose = getObjectPose(req.objectName)
    
    # These need to be in a dict, and depend on the object 
    # start_offset = float(req.startOffset) #FLOAT
    # ending_offset = float(req.endOffset) #FLOAT

    start_offset = 0.1
    ending_offset = 0.4
    rate = req.rate

    # Process args
    obj_y_val = copy.deepcopy(objPose.pose.position.y)  
    startPose = copy.deepcopy(objPose)
    endPose = copy.deepcopy(objPose)
    startPose.pose.position.y = (obj_y_val - start_offset)
    endPose.pose.position.y = (obj_y_val + ending_offset)

    # Put args into hash object
    argNames = ['startPose', 'endPose', 'rate']
    argVals = [startPose, endPose, rate]
    args = arg_list_to_hash(argNames, argVals)

    return ActionExecutorSrvResponse(pa.push(**args))

#### SHAKE #####################################################################
def shake(req):
    objPose = getObjectPose(req.objectName)
    twist_range = req.twistRange
    rate = req.rate

    argNames = ['objPose', 'twist_range', 'rate']
    argVals = [objPose, twist_range, rate]
    args = arg_list_to_hash(argNames, argVals)

    return ActionExecutorSrvResponse(pa.shake(**args))

#### GRASP #####################################################################
def grasp(req):
    objPose = getObjectPose(req.objectName)
    return ActionExecutorSrvResponse(pa.grasp(objPose))

#### PRESS #####################################################################
def press(req):
    objPose = getObjectPose(req.objectName)
    hover_distance = req.hoverDistance
    press_amount = req.pressAmount
    rate = req.rate

    # Process args
    obj_z_val = copy.deepcopy(objPose.pose.position.z)  
    startPose = copy.deepcopy(objPose)
    endPose = copy.deepcopy(objPose)
    startPose.pose.position.z = (obj_z_val + hover_distance)
    endPose.pose.position.z = (obj_z_val + hover_distance - press_amount)

    # Put args into hash object
    argNames = ['startPose', 'endPose', 'rate']
    argVals = [startPose, endPose, rate]
    args = arg_list_to_hash(argNames, argVals)

    return ActionExecutorSrvResponse(pa.press(**args))

#### DROP ######################################################################
def drop(req):
    # Pull args
    objPose = getObjectPose(req.objectName)
    drop_height = req.dropHeight


    # Process args
    obj_z_val = copy.deepcopy(objPose.pose.position.z)  
    dropPose = copy.deepcopy(objPose)
    dropPose.pose.position.z = (obj_z_val + drop_height)

    # Put args into hash object
    argNames = ['objPose', 'dropPose']
    argVals = [objPose, dropPose]
    args = arg_list_to_hash(argNames, argVals)

    return ActionExecutorSrvResponse(pa.drop(**args))

################################################################################
################################################################################

## To call for any general action to be executed
# Performs checks and send to the appropriate srv
def action_executor(req):

    actionName = req.actionName
    argNames = req.argNames
    args = req.args # list of strings, should be compatible with action. 
    paramNames = req.paramNames
    paramSettings = req.params # list of floats, should be compatible with action

    assert(len(req.argNames) == len(req.args))
    assert(len(req.paramNames) == len(req.params))

    a = getCorrectAction(actionName)
    zipped_request = ActionRequest(actionName, argNames, args, paramNames, paramSettings)
    return a(zipped_request)

def raw_action_executor(req):
    actionName = req.actionName
    args = req.argVals
    params = req.params 

    # sets params
    actionInfo = actionInfoProxy(actionName).actionInfo
    argNames = actionInfo.executableArgNames
    paramNames = actionInfo.paramNames

    assert(len(argNames) == len(args))
    assert(len(paramNames) == len(params))

    action_executor(Action(actionName, argNames, paramNames, args, params))


# This just takes in one action, pulls param values, and sends to the 
# Appropriate srv, which takes care of the hardcodings call. 
def pddl_action_executor(req):
    actionName = req.actionName
    args = req.argVals

    # sets params
    actionInfo = actionInfoProxy(actionName).actionInfo
    argNames = actionInfo.executableArgNames
    paramNames = actionInfo.paramNames
    paramDefaults = actionInfo.paramDefaults

    assert(len(argNames) == len(args))

    action_executor(Action(actionName, argNames, paramNames, args, paramDefaults))

################################################################################
## UTIL 
def move_to_start(req):
    return MoveToStartSrvResponse(pa._move_to_start(req.limb))

def open_gripper(req):
    return OpenGripperSrvResponse(pa.gripper_open(req.position))
    
def close_gripper(req):
    return CloseGripperSrvResponse(pa.gripper_close(req.position))

def approach(req):
    return ApproachSrvResponse(pa.approach(req.pose))

################################################################################

def main():
    rospy.init_node("physical_agent_node")
    rospy.wait_for_service('/object_location_srv')

    global pa
    pa = PhysicalAgent()

    rospy.Service("move_to_start_srv", MoveToStartSrv, move_to_start)
    rospy.Service("open_gripper_srv", OpenGripperSrv, open_gripper)
    rospy.Service("close_gripper_srv", CloseGripperSrv, close_gripper)
    rospy.Service("approach_srv", ApproachSrv, approach)

    # Action Primitives
    # rospy.Service("push_srv", PushSrv, push)
    # rospy.Service("grasp_srv", GraspSrv, grasp)
    # rospy.Service("shake_srv", ShakeSrv, shake)
    # rospy.Service("press_srv", PressSrv, press)
    # rospy.Service("drop_srv", DropSrv, drop)

    rospy.Service("action_executor_srv", ActionExecutorSrv, action_executor)
    rospy.Service("pddl_action_executor_srv", PddlExecutorSrv, pddl_action_executor)
    rospy.Service("raw_action_executor_srv", RawActionExecutorSrv, raw_action_executor)

    rospy.spin()

    return 0 
################################################################################

if __name__ == "__main__":
    main()
