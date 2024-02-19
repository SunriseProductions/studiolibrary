# Copyright 2020 by Kurt Rathjen. All Rights Reserved.
#
# This library is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. This library is distributed in the
# hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library. If not, see <http://www.gnu.org/licenses/>.
"""
NOTE: Make sure you register this item in the config.
"""
import re
import os
import logging

from studiolibrarymaya import mayafileitem

try:
    #import mutils
    import mutils.gui
    import maya.cmds as cmds
except ImportError as error:
    print(error)

#***********#
#* GLOBALS *#
#***********#
logger = logging.getLogger(__name__)

PREFAB_NAME_ATTR = "prefab_name"

#*************#
#* FUNCTIONS *#
#*************#

def save(path: str, root_node:str, *args, **kwargs):
    """
    Convenience function for saving an PrefabItem.
    
    Args:
        path (str): The path to save to
        root_node (str): The prefab rig to save
    """
    if not cmds.objExists(root_node):
        raise ValueError(f"The given node '{root_node}' does not exist!")

    if not cmds.attributeQuery("isPrefab", node = root_node, exists=True):
        raise ValueError(f"The given node {root_node} is not a prefab rig root node!")


    #? Select the root_node
    cmds.select(root_node, r=True)

    #? Save the prefabitem
    PrefabItem(path).save(*args, **kwargs)

def load(path, *args, **kwargs):
    """Convenience function for loading an PrefabItem."""
    PrefabItem(path).load(*args, **kwargs)

def remove_namespace_from_node(node):
    """
    Deletes the given node's namespace, if it has one

    Args:
        node (str): The node to rename
    
    Returns:
        str: The new node name
    """
    
    try:
        # Note rsplit instead of split
        namespace, name = node.rsplit(":", 1)
    except:
        namespace, name = None, node

    if namespace:
        try:
            cmds.rename(node, name)
        except RuntimeError:
            # Can't remove namespaces from read-only nodes
            # E.g. namespaces embedded in references
            pass

def swap_namespace(ns, target_ns):
    """
    Moves the contents of the given namespace to the target namespace.
    Will create the target namespace if it does not exist.
    Moving to the root namespace (':') will delete the given namespace.

    Args:
        ns (str): The namespace to move
        target_ns (str): The target namespace to move to.
    """
    #? Raise a valueError if ns does not exist
    if not cmds.namespace(exists=ns):
        raise ValueError(f"The given namespace '{ns}' does not exist in this scene!")

    #? If the target_ns does not exist, create it
    if not cmds.namespace(exists=target_ns):
        cmds.namespace(add=target_ns)
    
    #? Move the contents of ns to target_ns, and then delete ns
    cmds.namespace(mv=(ns, target_ns), f=True)
    cmds.namespace(rm=ns, force=True)

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

def list_all_namespaces():
    """
    Lists all namespaces in the current scene
    
    Returns:
        list: List of all namespaces in the scene
    """
    cmds.select(cl=True)
    cmds.namespace(setNamespace=':')
    namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)
    return namespaces

def find_namespaces(search_ns):
    """
    Finds a list of namespaces that contain the given search string

    Args:
        search_ns (str): The string to search for

    Returns:
        list[str]: A list of matching namespaces
    """
    #? Return early if there are no namepsaces in the current scene
    all_namespaces = list_all_namespaces()
    if not all_namespaces:
        logger.warning("No namespaces found in this scene!")
        return
    
    #? Add any matching namespaces to an output list, and return it
    output = list()
    for ns in all_namespaces:
        match = re.search(search_ns, ns)
        if match:
            output.append(match)

def get_cache_from_root(root_node):
    """
    Gets the prefab cache node from the given root node.

    Args:
        root_node (str): The root prefab rig node to query

    Returns:
        str: The name of the cache node
    """
    #? Make sure the given node its a valid prefab rig root node
    if not cmds.attributeQuery("isPrefab", node=root_node, exists=True):
        raise ValueError(f"The given node '{root_node}' is note a valid prefab rig!")
    
    #? Make sure the root_node has the cache node linked via the message attribute
    if not cmds.attributeQuery("usd_cycle_cache", node=root_node, exists=True):
        raise ValueError(f"The given node '{root_node}' has no USD cache linked to it!")
    
    #? Query the attribute to get the cache node and return it
    return cmds.listConnections(f"{root_node}.usd_cycle_cache")[0]

def get_namespace_from_cache(cacheNode):
    """
    Returns the root_node name for the prefab rig from a given cacheNode

    Args:
        cacheNode (str): Cache node to query

    Returns:
        str: Root node name
    """
    namespace, cacheNode = ":".join(cacheNode.split(":")[:-1]), cacheNode.split(":")[-1]
    #? Ensure the cache name of the correct length
    if len(cacheNode.split("_")) != 6:
        raise ValueError("Invalid name - Could not extract: asset_code, asset_descriptor, asset_mod, cycle_name, cycle_descriptor, cache_version")

    #? EXAMPLE CACHE NODE NAME: c027_shepherd_m00_tall_dancing_03
    #? EXAMPLE CACHE NODE NAME: {asset_code}_{asset_descriptor}_{asset_mod}_{cycle_name}_{cycle_descriptor}_{cache_version}
    asset_code, asset_descriptor, asset_mod, cycle_name, cycle_descriptor, cache_version = tuple(cacheNode.split("_"))
    
    #? Get the next instance
    #? ROOT NAME: {asset_code}_{asset_descriptor}_{asset_mod}_{cycle_descriptor}_{cycle_version} #_{instance}}
    instance = 0
    namespace = f"{asset_code}_{asset_descriptor}_{asset_mod}_{cycle_name}_{cycle_descriptor}"
    rig_name = "prefab"
    root_name = f"{namespace}:{rig_name}"

    keepGoing = True
    while keepGoing:
        #? Join the root_name str and the current instance, padded to three digits
        namespace = f"{asset_code}_{asset_descriptor}_{asset_mod}_{cycle_name}_{cycle_descriptor}"
        namespace = "_".join([namespace, f"{instance:03d}"])
        root_name = f"{namespace}:{rig_name}"

        if cmds.objExists(root_name):
            #? If the root_name exists, increment the instance and keep going
            keepGoing = True
            instance += 1
        else:        
            #? If the root_name does not exist, we found the next viable instance, so stop
            keepGoing = False
       
    return namespace

def get_namespace_from_root(root_node):
    """
    Checks if the root node has a prefab_name attribute, and returns it.
    If no attribute, return None instead.

    Args:
        root_node (str): Root node to query

    Returns:
        str or None: Given node's namespace
    """
    if not cmds.attributeQuery(PREFAB_NAME_ATTR, node = root_node, exists=True):
        return None
    
    base_namespace = cmds.getAttr(f"{root_node}.{PREFAB_NAME_ATTR}")
    
    cmds.namespace(setNamespace=':')
    all_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)

    #? Get the instance number
    instance = 0

    while True:
        namespace = f"{base_namespace}_{instance:03d}"
        if namespace not in all_namespaces:
            break
        
        instance += 1

    return namespace

def get_referenced_file_from_node(node):
    """
    Returns the reference file path for the given referenced node.

    Args:
        node (str): The node to query

    Returns:
        str: The reference filepath
    """
    #? Get the reference path and return it
    try: 
        ref_path = cmds.referenceQuery(node ,filename=True )
    except RuntimeError:
        #? Raise ValueError if the given node is not referenced:
        raise ValueError(f"The given node '{node}' is not referenced!")
    
    return ref_path

def swap_referenced_namespace(referenced_file, newNamespace):
    """
    Changes the namespace for the given referenced file to the new namespace

    Args:
        referenced_file (str): Filepath to the reference to change
       
         newNamespace (str): New namespace name
    """
    cmds.file(referenced_file, e=1, namespace=newNamespace)

def group_prefab(root_node, group_name = "__Prefabs__"):
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

class PrefabItem(mayafileitem.MayaFileItem):
    NAME = "Prefab"
    TYPE = "Prefab"
    EXTENSION = ".prefab"
    ICON_PATH = os.path.join(os.path.dirname(__file__), "icons", "animation.png")

    IMPORT_NAMESPACE = "PREFAB_IMPORT_TEMP"

    def __init__(self, *args, **kwargs):
        super(PrefabItem, self).__init__(*args, **kwargs)

    def save(self, **kwargs):
        """
        Saves the selected prefab rig node.
        
        The save method is called with the user values from the save schema.

        Args:
            kwargs (dict)

        """
        #? Make sure that a single prefab rig root node is selected
        #? Raise a value error if not.
        sel = cmds.ls(sl=True, type="transform")
        
        #? Filter the selection list to contain nodes with the 'isPrefab' attribute
        sel = [x for x in sel if cmds.attributeQuery("isPrefab", node=x, exists=True)]
        
        #? If nothing is selected, or if more than one object is selected, raise a ValueError
        if not sel or len(sel) > 1:
            raise ValueError("Please select a single Prefab rig's root transform.")

        #? Save the file item
        super(PrefabItem, self).save(**kwargs)
    
    def loadSchema(self, **kwargs):
        return [
            {
                "name": "namespace",
                "type": "string",
                "default": self.IMPORT_NAMESPACE,
                "persistent": True,
            },
        ]

    def load(self, **kwargs):
        """
        The load method is called with the user values from the load schema.

        Args:
            kwargs (dict)
        """
        #//return self._load_referenced(**kwargs)
        return self._load_imported(**kwargs)

    def _load_imported(self, **kwargs):
        """
        This load method imports the given prefab rig instead of referencing it.
        This allows for compatibility between multiple maya versions, as 
        referencing multiple duplicate prefab rigs in Maya 2024 causes a crash.

        Args:
            kwargs (dict)
        """
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
        root_node = None
        for x in new_nodes:
            if cmds.nodeType(x) != "transform":
                continue

            if cmds.attributeQuery("isPrefab", node = x, exists = True):
                root_node = x
                break

        if not root_node:
            raise ValueError(f"Could not find the prefab's root node: {self.transferPath}")


        #? Get the cache node for the given root node
        cache_node = get_cache_from_root(root_node)
        
        #? Get the namespace from the cache node
        new_namespace = get_namespace_from_root(root_node) or get_namespace_from_cache(cache_node)

        #? Swap to the new namespace
        swap_namespace(self.IMPORT_NAMESPACE, new_namespace)
        root_node = root_node.replace(self.IMPORT_NAMESPACE, new_namespace)
        
        #? Parent the root node to the prefabs group
        group_prefab(root_node)

    def _load_referenced(self, **kwargs):
        """
        This load method references the given prefab rig instead of importing it.
        This allows for compatibility between multiple maya versions, as 
        referencing multiple duplicate prefab rigs in Maya 2024 causes a crash.

        Args:
            kwargs (dict)
        """
        logger.info("Loading %s %s", self.path(), kwargs)

        new_nodes = cmds.file(
            self.transferPath(),
            reference=True,
            type="mayaAscii",
            options="v=0;",
            preserveReferences=True,
            mergeNamespacesOnClash=False, 
            namespace=self.IMPORT_NAMESPACE, 
            returnNewNodes=True
        )
        #//logger.debug(f"new_nodes: {new_nodes}")
        #? Get the imported root node
        root_node = None
        for x in new_nodes:
            if cmds.nodeType(x) != "transform":
                continue

            if cmds.attributeQuery("isPrefab", node = x, exists = True):
                root_node = x
                break

        if not root_node:
            raise ValueError(f"Could not find the prefab's root node: {self.transferPath}")

        #? Get the cache node for the given root node
        cache_node = get_cache_from_root(root_node)
        
        #? Get the namespace from the cache node
        new_namespace = get_namespace_from_root(root_node) or get_namespace_from_cache(cache_node)

        #? Get the reference path
        ref_path = get_referenced_file_from_node(root_node)
        
        #? Move the nodes to it's new namespace
        swap_referenced_namespace(ref_path, new_namespace)
        root_node = root_node.replace(self.IMPORT_NAMESPACE, new_namespace)
                                      
        #? Parent the root node to the prefabs group
        group_prefab(root_node)

        #? Get and rename the reference node
        all_reference_nodes = cmds.ls(f"*{self.IMPORT_NAMESPACE}*", type="reference")

        for ref in all_reference_nodes:
            ns = cmds.referenceQuery(ref, ns=True)
            ns = ns.strip(":")
            if new_namespace == ns:
                newName = f"{new_namespace}RN"
                cmds.lockNode(ref, l=False)
                cmds.rename(ref, newName)
                cmds.lockNode(newName, l=True)
                logger.debug(f"Renamed {ref} to {newName}")
                break
        
    def loadFromCurrentValues(self):
        """Load the mirror table using the settings for this item."""
        kwargs = self._currentLoadValues
        objects = cmds.ls(selection=True) or []

        try:
            self.load(objects=objects, **kwargs)
        except Exception as error:
            self.showErrorDialog("Item Error", str(error))
            raise
