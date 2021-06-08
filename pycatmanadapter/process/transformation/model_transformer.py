from pycatmanadapter.log import logger
from joblib import Parallel, delayed
from pycatmanadapter.process.transformation import constants
from pycatmanadapter.process.transformation.utils import TransformationUtils as tutils


class ModelTransformer:

    # ModelTransformer Constructor
    #
    # Parameters:
    #
    # payload : Input payload
    # config : Mapping configuration

    def __init__(self, payload, config):
        self.map = self.__mapper(payload, config)
        self.hash_table = dict()

    # Mapper Method
    #
    # Parameters:
    #
    # payload : Input payload
    # config : Mapping configuration

    def __mapper(self, payload, config):
        outbound_list = []

        chunked_items = list(tutils.chunk(payload, constants.CHUNK_VAL))
        logger.debug("Input payload chunked in order to be processed parallely")

        outbound_list = outbound_list + (
            Parallel(n_jobs=-1, prefer="threads")(delayed(self.__process_seg)(config, item) for item in chunked_items))
        return outbound_list[0]

    # Iterate parallely over chunked items list
    #
    # Parameters:
    #
    # config : Mapping configuration
    # chunked_items : List of chunked items

    def __process_seg(self, config, chunked_items):
        return (
            Parallel(n_jobs=-1, prefer="threads")(delayed(self.__segment_mapper)(config, item) for item in chunked_items))

    # Map segment and fields
    #
    # Parameters:
    #
    # segment_config : segment config from config yaml
    # item : List of item from each chunked items

    def __segment_mapper(self, segment_config, item):
        seg_dict = dict()
        field_list = segment_config.get('fieldMapping')
        for field_obj in field_list:
            val = self.__field_mapper(field_obj, item)
            target_val = field_obj.get('targetField')
            if val is not None:
                seg_dict[target_val.lower()] = val
        return seg_dict

    # Map fields available in a segment config
    #
    # Parameters:
    #
    # field_config : Segment chunk from config payload
    # item : List of item from each chunked items

    def __field_mapper(self, field_config, item):
        if hasattr(field_config, 'Condition'):
            mapping_cond = field_config.get('Condition')
        else:
            mapping_cond = None
        source_field_path = field_config.get('sourceField')
        field_dict = self.__map_each_field(source_field_path, item, mapping_cond)
        return field_dict

    # Map each fields using mapping condition
    #
    # Parameters:
    #
    # source_path : Source field path
    # item : List of item from each chunked items
    # mapping_cond : Condition

    def __map_each_field(self, source_path, item, mapping_cond):
        ret_val = None
        if mapping_cond is None:
            path_list = source_path.split(".")
            val = tutils.get_data(item, 0, path_list)
            return val
        else:
            path_array = source_path.split(".")
            for options in mapping_cond.get('options'):
                if hasattr(options, 'eq'):
                    map_cond_array = options.get('eq').get('field').split(".")
                    map_cond_val = options.get('eq').get('value')
                    diverge_node = tutils.find_common_node(path_array, map_cond_array)
                    itr = 0
                    current_seg = item
                    while itr < len(path_array):
                        if type(current_seg) != type([1, 2]):
                            if hasattr(current_seg, path_array[itr]):
                                current_seg = eval('var' + '.' + path_array[itr])
                                if diverge_node == path_array[itr]:
                                    ret_val = self.__fetch_field(map_cond_array, current_seg, path_array, itr,
                                                               map_cond_val)
                                    break
                                itr = itr + 1
                            else:
                                return ret_val
                        else:
                            current_seg = current_seg[0]
            return ret_val

    # Fetch each field using mapping condition and source field
    # Returns field value if mapping condition is true
    #
    # Parameters:
    #
    # cond_field_list : Condition field list
    # current_seg : List of item in current segment
    # src_field_list : Source mapped field list
    # itr : Iterator after diverged field, such that re traversal of field is skipped
    # cond_val : condition resolved value

    def __fetch_field(self, cond_field_list, current_seg, src_field_list, itr, cond_val):
        itr = itr + 1
        temp = itr
        for items in current_seg:
            var = items
            while itr < len(cond_field_list):
                if hasattr(var, cond_field_list[itr]):
                    var = eval('var.' + cond_field_list[itr])
                    if var is not None:
                        itr += 1
                else:
                    return None
            if str(var) == cond_val:
                itr = temp
                val = tutils.get_data(items, itr, src_field_list)
                return val
            itr = temp
