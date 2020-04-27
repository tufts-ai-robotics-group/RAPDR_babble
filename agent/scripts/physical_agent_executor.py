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
from environment.srv import ObjectLocationSrv
from util.physical_agent import PhysicalAgent
from util.action_request import ActionRequest

pa = None
obj_location_srv = rospy.ServiceProxy('object_location_srv', ObjectLocationSrv)

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
#### PUSH ######################################################################
def push(req):
    # Pull args
    objPose = getObjectPose(req.objectName)
    start_offset = float(req.startOffset) #FLOAT
    ending_offset = float(req.endOffset) #FLOAT
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

    return PushSrvResponse(pa.push(**args))

################################################################################
#### SHAKE #####################################################################
def shake(req):
    # Pull args
    objPose = getObjectPose(req.objectName)
    twist_range = req.twistRange
    rate = req.speed

    # Put args into hash object
    argNames = ['objPose', 'twist_range', 'rate']
    argVals = [objPose, twist_range, rate]
    args = arg_list_to_hash(argNames, argVals)

    return ShakeSrvResponse(pa.shake(**args))

################################################################################
#### GRASP #####################################################################
def grasp(req):
    # Pull args
    objPose = getObjectPose(req.objectName)
    return GraspSrvResponse(pa.grasp(objPose))

################################################################################
#### PRESS #####################################################################
def press(req):
    # Pull args
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

    return PressSrvResponse(pa.press(**args))

################################################################################
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

    return DropSrvResponse(pa.drop(**args))

################################################################################
def action_executor(req):
    ## To call for any general action to be executed

    actionName = req.actionName
    argNames = req.argNames
    args = req.args # list of strings, should be compatible with action. 
    paramNames = req.paramNames
    paramSettings = req.params # list of floats, should be compatible with action

    assert(len(argNames) == len(args))
    assert(len(paramNames) == len(paramSettings))

    ## Just do push for now setExecutionArgNames
    a = getCorrectAction(actionName)
    request = ActionRequest(actionName, argNames, args, paramNames, paramSettings)

    a(request)
    return ActionExecutorSrvResponse(1)

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

def arg_list_to_hash(argNames, argValues):
    args = {}
    for i in range(len(argValues)):
        name = argNames[i]
        val = argValues[i]
        if not(val == 0.0 or val == None or val == 0):
            args[name] = val
    return args

################################################################################

def main():
    rospy.init_node("physical_agent_node")
    rospy.wait_for_service('/object_location_srv')

    global pa
    pa = PhysicalAgent()

    s_1 = rospy.Service("move_to_start_srv", MoveToStartSrv, move_to_start)
    s_2 = rospy.Service("open_gripper_srv", OpenGripperSrv, open_gripper)
    s_2 = rospy.Service("close_gripper_srv", CloseGripperSrv, close_gripper)
    s_3 = rospy.Service("approach_srv", ApproachSrv, approach)

    # Action Primitives
    s_4 = rospy.Service("push_srv", PushSrv, push)
    s_5 = rospy.Service("grasp_srv", GraspSrv, grasp)
    s_6 = rospy.Service("shake_srv", ShakeSrv, shake)
    s_7 = rospy.Service("press_srv", PressSrv, press)
    s_8 = rospy.Service("drop_srv", DropSrv, drop)
    s_9 = rospy.Service("action_executor_srv", ActionExecutorSrv, action_executor)
    s_10 = rospy.Service("pddl_action_executor_srv", ActionExecutorSrv, action_executor)

    rospy.spin()

    return 0 
################################################################################

if __name__ == "__main__":
    main()
