import re, six

class SelectExtractors:
    """
    The functions in this class should be called after executing an ES query. Some functions will
    be called if the grouper is not invoked (e.g. extractSimpleSelect), others should
    be called after the grouper is invoked.
    """

    @staticmethod
    def extractSimpleSelect(frames_list, simpleSelectDict):
        """

        :param frames_list: the retrieved_frames
        :param simpleSelectDict: meant to represent 'simple' select instances. Each key
        maps to a list that contains exactly one value
        :return: a list of dictionaries. If a field from simpleSelectDict
        is not found in the frame, that field will not be returned in the dict.
        It is possible for dictionaries to be completely empty! The returned
        list will have same length as frames_list
        """
        answer = []
        for frame in frames_list:
            tmp = {}
            for key, val in simpleSelectDict.items():
                if len(val) != 1:
                    #at present, this is the right strategy. In future, we should figure
                    #out a way to 'combine' the various val properties
                    raise Exception('postprocess simpleSelectDict! List does not meet specs')

                if list(val)[0] in frame['_source']:
                    tmp[key] = (frame['_source'][list(val)[0]])
            answer.append(tmp)
        return answer

    @staticmethod
    def extractCountSelect(grouped_frames, countSelectDict):
        """
        We don't do any post-processing on the groups at present (e.g. if field is MISSING_FIELD)
        :param grouped_frames: a dictionary where each key (the value of a 'grouped variable') maps to
         a list of (complete) frames. Typically output by a method in Grouper (e.g. standard_grouper)
        :param countSelectDict: the countSelectDict dictionary created as part of the output in
        SparqlTranslator._populate_list_set_data_structure
        :return: a dictionary with the same keys as grouped_frames, and the value as a
        dict that has count variables for keys and the actual count for values.
        """
        # at present, we throw an exception if countSelectDict contains any list values
        # with more than one element.

        if not countSelectDict:
            return None

        answer = {}

        for var, properties in countSelectDict.items():
            if len(properties) != 1:
                string = var+" doesn't have exactly one mapped property in count-select!"
                raise Exception(string)

        for key, group in grouped_frames.items():
            count_vars = {}
            SelectExtractors._init_count_vars(count_vars, countSelectDict)
            SelectExtractors._update_count_vars(count_vars, group)
            tmp = {}
            for k, v in count_vars.items():
                tmp[k] = v['count']
            answer[key] = tmp

        return answer

    @staticmethod
    def extractGroupConcatSelect(grouped_frames, groupConcatSelectDict):
        """

        :param grouped_frames: a dictionary where each key (the value of a 'grouped variable') maps to
         a list of (complete) frames
        :param groupConcatSelectDict: the groupConcatSelectDict dictionary created as part of the output in
        SparqlTranslator._populate_list_set_data_structure
        :return: a dictionary with the same keys as grouped_frames, and the value as a
        dict that has the group-concat variable for the key and the output string as value.
        """
        # at present, we throw an exception if groupConcatSelectDict contains any list values
        # with more than one element.

        if not groupConcatSelectDict:
            return None

        answer = {}
        print groupConcatSelectDict
        for var, properties in groupConcatSelectDict.items():
            if len(properties['properties']) != 1:
                string = var+" doesn't have exactly one mapped property in group-concat select!"
                raise Exception(string)

        for key, group in grouped_frames.items():
            group_concat_vars = {}
            SelectExtractors._init_group_concat_vars(group_concat_vars, groupConcatSelectDict)
            SelectExtractors._update_group_concat_vars(group_concat_vars, group)
            tmp = {}
            for k, v in group_concat_vars.items():
                tmp[k] = v['group_concat_string']
            answer[key] = tmp

        return answer

    @staticmethod
    def _init_count_vars(count_vars, countSelectDict):
        """
        Modifies count_vars
        :param count_vars: an empty dictionary that will get initialized with all the information
        we need so that we can keep updating it as we encounter frames. It has the same keys
        as countSelectDict, and two 'inner' keys: 'properties' and 'count'.
        :param countSelectDict: the countSelectDict dictionary created as part of the output in
        SparqlTranslator._populate_list_set_data_structure
        :return: None
        """
        if count_vars:
            raise Exception('count_vars is not empty in SelectExtractors._init_count_vars')

        for var, properties in countSelectDict.items():
            tmp = {}
            tmp['properties'] = properties
            tmp['count'] = 0
            count_vars[var] = tmp

    @staticmethod
    def _init_group_concat_vars(group_concat_vars, groupConcatSelectDict):
        """
        Modifies group_concat_vars
        :param group_concat_vars: an empty dictionary that will get initialized with all the information
        we need so that we can keep updating it as we encounter frames. It has the same keys
        as groupConcatSelectDict, and four 'inner' keys: 'properties', 'group_concat_list',
        'separator' and 'distinct'. Later, when updating, 'group_concat_string' will be added.
        :param groupConcatSelectDict: the groupConcatSelectDict dictionary created as part of the output in
        SparqlTranslator._populate_list_set_data_structure
        :return: None
        """
        if group_concat_vars:
            raise Exception('group_concat_vars is not empty in SelectExtractors._init_group_concat_vars')

        for var, values in groupConcatSelectDict.items():
            tmp = {}
            tmp['properties'] = values['properties']
            tmp['group_concat_list'] = []
            tmp['separator'] = values['separator']
            tmp['distinct'] = values['distinct']
            group_concat_vars[var] = tmp

    @staticmethod
    def _update_group_concat_vars(group_concat_vars, group):
        """
        Modifies group_concat_vars. Be wary of semantics. If we encounter a list/string, we will append
        to ground_concat_list (original list structure gets merged).
        A new inner field called 'group_concat_string' will be added once we are finished processing a group.
        :param group_concat_vars: see _init_group_concat_vars for a description of the data structure
        :param group: a list of retrieved frames representing a group
        :return: None
        """
        for ds in group_concat_vars.itervalues():
            prop = list(ds['properties'])[0]  # this is a hacky line. It should be superseded,
                                        #since there could be more than one property
            for frame in group:
                if prop in frame:
                    tmp = []
                    if isinstance(frame[prop], list):
                        tmp += frame[prop]
                    elif isinstance(frame[prop], six.string_types):
                        tmp.append(frame[prop])
                    else:
                        raise Exception('Abnormal data type')
                    ds['group_concat_list'] += tmp
            if ds['distinct']:
                q = list(set(ds['group_concat_list']))
            else:
                q = ds['group_concat_list']
            ds['group_concat_string'] = ds['separator'].join(q)


    @staticmethod
    def _update_count_vars(count_vars, group):
        """
        Modifies count_vars. Be wary of semantics. The name_count is treated differently; otherwise
        for each occurrence .
        :param count_vars: see _init_count_vars for a description of the data structure
        :param group: a list of retrieved frames representing a group
        :return: None
        """
        for ds in count_vars.itervalues():
            prop = list(ds['properties'])[0]  # this is a hacky line. It should be superseded,
                                        #since there could be more than one property
            for frame in group:
                if prop in frame:
                    count = 1
                    if prop == 'name_count':    # for the 'number_of_individuals' case, an xsd:integer
                                                #change name_count to whatever 'number_...' is mapped to
                                                #in MappingTable
                        count = SelectExtractors._parseXSDIntegerLiteral(frame['name_count'])

                    ds['count'] += count


    @staticmethod
    def _parseXSDIntegerLiteral(str):
        """
        For parsing XSD integer literals to integer
        :param str: e.g. "\"5\"^^xsd:integer"
        :return: 5
        """
        l = (re.split("\^\^|\"", str))
        if l[3]=='xsd:integer':
            return int(l[1])

