"""
NOTE: Make sure you register this item in the config.
"""
#* IMPORTS *#
import os
import logging
import json
import re
import glob
from importlib import reload

#* sunrise
import sun_maya.anim_pre_fab.core.clusters as clustersFn
import sun_maya.anim_pre_fab.core.rig as rigFn


import studiolibrary

from studiovendor.Qt import QtGui
from studiovendor.Qt import QtCore
from studiovendor.Qt import QtWidgets

from studiolibrarymaya import baseitem, baseloadwidget, basesavewidget, mayafileitem, animitem, prefabitem

try:
    import mutils
    import maya.cmds as cmds
except ImportError as error:
    print(error)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

#* FUNCTIONS *#
def save(path: str, root_node:str, *args, **kwargs):
    """
    Convenience function for saving an PrefabCluster Item.
    
    Args:
        path (str): The path to save to
        root_node (str): The prefab rig to save
    """
    if not cmds.objExists(root_node):
        logger.error("The given node '%s' does not exist!" % root_node)
        return

    if not clustersFn.is_prefab_cluster(root_node):
        logger.error("The given node '%s' is not a prefab rig root node!" % root_node)
        return


    #? Select the root_node
    cmds.select(root_node, r=True)

    #? Save the prefabitem
    PrefabClusterItem(path).save(*args, **kwargs)

def load(path, *args, **kwargs):
    """Convenience function for loading an PrefabCluster Item."""
    PrefabClusterItem(path).load(*args, **kwargs)

def remove_namespace(ns):
    """
    Deletes the given namespace from this scene

    Args:
        ns (str): The namespace to delete
    """
    
    #? Empty the given namespace
    try:
        cmds.namespace(mv = (ns, ":"), force=True)
    except Exception as e:
        logger.warning(f"Could not empty the given namespace {ns}")
        raise e
    
    #? Delete the (now empty) given namespace
    cmds.namespace(rm = ns, force=True)

def group_prefab_cluster(root_node, group_name = "__Prefabs__"):
    """
    Parents the given root node to the Prefabs group. If the 
    group does not exist in the current scene, it will be created
    first.

    Args:
        root_node (str): The prefab root node to group
        group_name (str): The name of the group node to parent to. Defaults to "__Prefabs__"
    
    Returns:
        bool: True if successful, False if not
    """ 
    if not cmds.objExists(group_name):
        grp = cmds.createNode("transform", name = group_name)
        logger.info(f"The prefab group node '{grp}' did not exist, and has been created.")
    else:
        grp = group_name
        logger.info(f"Found prefab group node '{grp}'.")
    
    try:
        cmds.parent(root_node, grp)
    except Exception as e:
        print(e)
        return False
    return True

def is_prefab(node):
    """
    Checks if the given node is a Prefab.

    :param node: The node to query
    :type node: str

    :returns: True if the node is a Prefab, False if not
    :rtype: bool
    """  
    if not cmds.objExists(node):
        logger.error("%s does not exist!", node)
        return False
    return cmds.attributeQuery("isPrefab", node=node, exists=True)

def is_prefab_cluster(node):
    """
    Checks if the given node is a PrefabCluster.

    :param node: The node to query
    :type node: str

    :returns: True if the node is a Cluster, False if not
    :rtype: bool
    """    
    if not cmds.objExists(node):
        logger.error("%s does not exist!", node)
        return False
    return cmds.attributeQuery("isPrefabCluster", node=node, exists=True)

#* CLASSES *#
class PrefabClusterLoadWidget(baseloadwidget.BaseLoadWidget):
    pass

class PrefabClusterSaveWidget(basesavewidget.BaseSaveWidget):
    pass

class PrefabClusterItem(mayafileitem.MayaFileItem):

    NAME = "PrefabCluster"
    TYPE = NAME
    EXTENSION = ".prefabcluster"
    ICON_PATH = os.path.join(os.path.dirname(__file__), "icons", "selectionSet.png")
    LOAD_WIDGET_CLASS = PrefabClusterLoadWidget
    SAVE_WIDGET_CLASS = PrefabClusterSaveWidget
    IMPORT_NAMESPACE = "PREFAB_CLUSTER"

    def transferPath(self):
        return self.path() + "/mayafile.ma"

    def jsonPath(self):
        return self.path() + "/cluster.json"
    
    def prefabAnimPath(self):
        return self.path() + "/prefabAnim"
    
   
    def _save_json(self, data):
        with open(self.jsonPath(), "w") as fp:
            json.dump(data, fp)
        logger.info("Exported json data to %s", self.jsonPath())


    def save(self, **kwargs):
        """
        Exports the selected Prefab Cluster node.
        The save method is called with the user values from the save schema.

        Args:
            kwargs (dict)        
        """
        sel = cmds.ls(sl=True, type="transform")
        
        #? Filter the selection list to contain nodes with the 'isPrefab' attribute
        sel = [x for x in sel if cmds.attributeQuery("isPrefabCluster", node=x, exists=True)]
        
        #? If nothing is selected, or if more than one object is selected, raise a ValueError
        if not sel or len(sel) > 1:
            raise ValueError("Please select a single PrefabCluster transform.")

        cmds.select(sel[0], r=True)
        cmds.parent(sel[0], world=True)
        
        #export_data = {"name" : sel[0], "prefabs" : []}
        #cluster = clustersFn.PrefabCluster(sel[0])
        

        #* Export animItems for each prefab
        '''
        for prefab_dict in cluster.prefabs:
            prefab_node = prefab_dict.get("name")
            logger.debug("prefab_node: %s" % prefab_node)
            prefab_name = prefab_dict.get("name").replace(":", "_")[0] # strip out the namespace
            logger.debug("prefab_name: %s" % prefab_name)
            source_path = prefab_dict.get("rig_path")
            prefab = cluster.get_prefab_wrapper(prefab_node)
            objects = prefab.controls
            logger.debug("objects: %s" % objects)

            anim_path = os.path.join(self.prefabAnimPath(), f"{prefab_name}.anim")
            if not os.path.exists(anim_path):
                os.makedirs(anim_path, exist_ok=True)
            
            animitem.save(anim_path, objects=objects)
            
            data = {
                "name" : prefab_name, 
                "source_path" : source_path, 
                "anim_path" : anim_path
            }
            export_data["prefabs"].append(data)
        '''
            
        #? Save the maya file item
        super(PrefabClusterItem, self).save(**kwargs)
        cmds.parent(sel[0], clustersFn.ROOT_GROUP)

        #//#? Save the JSON data
        #//self._save_json(export_data)

    def load(self, **kwargs):
        """
        The load method is called with the user values from the load schema.

        Args:
            kwargs (dict)
        """
        return self._load_imported(**kwargs)

    def _load_imported(self, **kwargs):
        logger.info("Loading %s %s", self.path(), kwargs)

        new_nodes = cmds.file(
            self.transferPath(), 
            i=True,
            options="v=0;", 
            mergeNamespacesOnClash=False,
            namespace = self.IMPORT_NAMESPACE,
            returnNewNodes = True
        )

        #? Get the imported root node
        old_container = None
        root_node = None
        for x in new_nodes:
            if cmds.nodeType(x) != "transform":
                continue
            
            if cmds.attributeQuery("isPrefabCluster", node = x, exists = True):
                root_node = x
                break

        if not root_node:
            raise ValueError(f"Could not find the prefab cluster's root node: {self.transferPath()}")
        logger.debug("root_node: %s" % root_node)
        prefabs = [x for x in cmds.listRelatives(root_node, c=True) if rigFn.is_prefab(x)]
        
        
        duplicate_cluster = root_node.split(":")[-1]
        new_namespace = f"{duplicate_cluster}_0"
        duplicate_clusters = cmds.ls(f"*:{duplicate_cluster}")
        if duplicate_cluster:
            new_namespace = f"{duplicate_cluster}_{len(duplicate_cluster)}"
            
        
        cmds.parent(root_node, clustersFn.ROOT_GROUP)
        prefabitem.swap_namespace(self.IMPORT_NAMESPACE, new_namespace)
        root_node = root_node.replace(self.IMPORT_NAMESPACE, new_namespace)
        
        

    def load_from_json(self, **kwargs):
        #* Read JSON data
        with open(self.jsonPath(), "r") as fp:
            data = json.load(fp)

        #*  Create the cluster
        cluster = clustersFn.PrefabCluster(data["name"])

        #* For each prefab, import it and parent it to this cluster
        for prefab_data in data["prefabs"]:
            src_path = prefab_data["source_path"]
            if not os.path.exists(src_path):
                logger.error("Could not load prefab: %s" % src_path)
                continue
            
            all_prefabs = [x for x in cmds.ls(type="transform") if rigFn.is_prefab(x)]
            
            #* Load the prefab
            prefabitem.load(src_path)
            
            #* Get the root imported node
            prefab_node = [x for x in cmds.ls(type="transform") if rigFn.is_prefab(x) and x not in all_prefabs][0]

            #* Add prefab to cluster
            cluster.add_prefab(prefab_node)
            prefab = cluster.get_prefab_wrapper(prefab_node)
            
            anim_path = prefab_data["anim_path"]
            if not os.path.exists(anim_path):
                LOGGER.warning("No animation found: %s" % anim_path)
                continue
            #* Load the animation
            animitem.load(anim_path, objects=prefab.controls)

    def loadSchema(self, **kwargs):
        return [
            {
                "name": "namespace",
                "type": "string",
                "default": self.IMPORT_NAMESPACE,
                "persistent": True,
            },
        ]


