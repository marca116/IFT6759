import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.globals import set_debug

openai_api_key = os.environ.get('OPENAIKEY')

# template = """
#     List of predicates: ['city_of_birth', 'country_of_birth', 'city_of_death', 'children', 'countries_of_residence', 'identity', 'date_of_death', 'schools_attended', 'website', 'date_of_birth', 'alternate_names', 'charges', 'member_of', 'stateorprovince_of_death', 'stateorprovince_of_death','founded_by', 'spouse', 'employee_of', 'shareholders', 'parents', 'religion', 'founded', 'country_of_death', 'members', 'origin', 'employees', 'political/religious_affiliation', 'cities_of_residence', 'age', 'title', 'city_of_branch', 'dissolved', 'stateorprovince_of_birth', 'other_family', 'cause_of_death', 'stateorprovince_of_branch', 'country_of_branch', 'stateorprovinces_of_residence', 'siblings']\n\n
#     You are a relation extractor that extracts entities and their relations from a text. For example, given a sentence: "Barack Obama was born in Honolulu, Hawaii.", a relation classifier aims at predicting the relation of city_of_birth. Your task is to extract the relations and entities mentioned in the given context. These terms should represent the key entities and relations in the given text. \n Thought 1: While traversing through each sentence, Think about the key entities mentioned in it.\n \Entities may include objects, locations (country, city, etc.), organizations, persons, concepts, etc.\n \Entities should be as atomistic as possible\n\n Thought 2: Think about how these entities can have one on one relation with other entities.\n Entities can be related to many other entities\n\n Thought 3: Find out the relation between each such related pair of entities.\n\n Thought 4: You can create new predicates, but they need to be in the same format as the given predicates (ex: X president Y).\n\n Thought 5: Dates need include the year, month and day. If some of that information is missing, the object should be 'missing_info'. Thought 6: Ignore relations with unknown subject or object. \n\n
#     Format your output as a list of json. Each element of the list contains a pair of entities and the relation between them, like the following: \n
#     [\n
#        {{\n
#            "subject": "[name]",\n
#            "predicate": "[name]",\n
#            "object": "[name]"
#        }}, 
#        ...
#     ]
#     {task}
# """

# template = """
#     List of predicates: ['country_of', 'stateorprovince_of', 'city_of_birth', 'country_of_birth', 'city_of_death', 'children', 'countries_of_residence', 'identity', 'date_of_death', 'schools_attended', 'website', 'date_of_birth', 'alternate_names', 'charges', 'member_of', 'stateorprovince_of_death', 'stateorprovince_of_death','founded_by', 'spouse', 'employee_of', 'shareholders', 'parents', 'religion', 'founded', 'country_of_death', 'members', 'origin', 'employees', 'political/religious_affiliation', 'cities_of_residence', 'age', 'title', 'city_of_branch', 'dissolved', 'stateorprovince_of_birth', 'other_family', 'cause_of_death', 'stateorprovince_of_branch', 'country_of_branch', 'stateorprovinces_of_residence', 'siblings']\n\n
#     You are a relation extractor that extracts entities and their relations from a text. For example, given a sentence: "Barack Obama was born in Honolulu, Hawaii.", a relation classifier aims at predicting the relation of city_of_birth. Your task is to extract the relations and entities mentioned in the given context. These terms should represent the key entities and relations in the given text. You also need to determine what attributes does each entity have. An attribute can be any property of the entity that is specified in the text. It could be a quality, a fault, a physical characteristic, etc. Something can't be both a relation or an attribute, pick one and prioritise relations. \n Thought 1: While traversing through each sentence, Think about the key entities mentioned in it.\n \Entities may include objects, locations (country, city, etc.), organizations, persons, concepts, etc.\n \Entities should be as atomistic as possible\n\n Thought 2: Think about how these entities can have one on one relation with other entities.\n Entities can be related to many other entities\n\n Thought 3: Find out the relation between each such related pair of entities. \n\n Thought 4: All dates need to include the year, month and day. Ignore relations with unknown subject or object. \n\n
#     Format your output as a list of json. Each element of the list contains a pair of entities and the relation between them, like the following: \n
#     {{
#     "relations":[\n
#        {{\n
#            "subject": "[name]",\n
#            "predicate": "[name]",\n
#            "object": "[name]"
#        }}, 
#        ...
#     ],
#     "attributes":[\n
#        {{\n
#            "entity_name": "[name]",\n
#            "attributes": ["[name]"],
#        }}, 
#        ...
#     ]
#     }}
#     {task}
# """

# template = """
#     You are a relation extractor tasked with identifying entities and their relations from textual content. Your objective is to discern the key entities within a given text and ascertain the relations among them based on a predefined list of predicates. The entities could encompass a variety of concepts, including but not limited to individuals, organizations, locations (such as countries, cities, etc.), and other identifiable objects or concepts.\n\n
#     When analyzing the text, focus on extracting entities that are explicitly mentioned and determine how they are interconnected through one-on-one relationships. Make sure to justify why this relation apply to these entities. It is crucial to use only the following list of predicates to define the relationships between entities: ['country_of', 'stateorprovince_of', 'city_of_birth', 'country_of_birth', 'city_of_death', 'children', 'country_of_residence', 'identity', 'date_of_death', 'schools_attended', 'website', 'date_of_birth', 'alternate_names', 'charges', 'member_of', 'stateorprovince_of_death', 'stateorprovince_of_death','founded_by', 'spouse', 'employee_of', 'shareholders', 'parents', 'religion', 'founded', 'country_of_death', 'members', 'origin', 'employees', 'political/religious_affiliation', 'city_of_residence', 'age', 'title', 'city_of_branch', 'dissolved', 'stateorprovince_of_birth', 'other_family', 'cause_of_death', 'stateorprovince_of_branch', 'country_of_branch', 'province_of_residence', 'state_of_residence','siblings'].\n\nYour results should be structured as a list of JSON objects, each representing a pair of entities and the relation between them, guided by the predicates from the list above. Additionally, identify any attributes of the entities mentioned in the text. An attribute could be any characteristic, quality, or identifiable feature of an entity as specified in the context. The format of your output should be as follows:\n
#     {{
#         "relations": [
#             {{
#                 "subject": "[entity1]",
#                 "predicate": "[predicate from the list]",
#                 "object": "[entity2]",
#                 "justification": "[reason]"
#             }},
#             ...
#         ],
#         "attributes": [
#             {{
#                 "entity_name": "[entity]",
#                 "attributes": ["[attribute]", ...]
#             }},
#             ...
#         ]
#     }}\n\n
#     Remember, all dates must include the year, month, and day. Disregard any relations with unknown subjects or objects, and ensure that predicates strictly adhere to the provided list.\n\n
#     {task}
# """

# IMPORTANT : Doesn't work

# template = """
#     You are a relation extractor tasked with identifying entities and their relations from textual content. Your objective is to discern the key entities within a given text and ascertain the relations among them based on a predefined list of predicates. The entities could encompass a variety of concepts, including but not limited to individuals, organizations, locations (such as countries, cities, etc.), dates, and other identifiable objects or concepts.\n\n
#     When analyzing the text, focus on extracting entities that are explicitly mentioned and determine how they are interconnected through one-on-one relationships. Make sure to justify why this relation apply to these entities. It is crucial to use only the following list of predicates to define the relationships between entities: [parent_of, child_of, spouse_of, member_of, employed_by, follow_religion, has_job, date_of_birth, date_of_death, part_of_#LOCATION_TYPE#, born_in_#LOCATION_TYPE#, died_in_#LOCATION_TYPE#, resides_in_#LOCATION_TYPE#]. #LOCATION_TYPE# needs to be replaced by the correct location type: country, state, municipality, city, etc. \n\nImportantly, when a date is mentioned in the text, treat it as an entity and establish a relationship with the relevant individual using the 'date_of_birth' or 'date_of_death' predicates. For example, if the text states that an individual died on a specific date in a specific location, extract and define the relations to include 'died_in_#LOCATION_TYPE#' with the location and 'date_of_death' with the specified date.\n\nYour results should be structured as a list of JSON objects, each representing a pair of entities and the relation between them, guided by the predicates from the list above. Additionally, identify any attributes of the entities mentioned in the text. An attribute could be any characteristic, quality, or identifiable feature of an entity as specified in the context. The format of your output should be as follows:\n
#     {{
#         "relations": [
#             {{
#                 "subject": "[entity1]",
#                 "predicate": "[predicate from the list]",
#                 "object": "[entity2]"
#             }},
#             ...
#         ],
#         "attributes": [
#             {{
#                 "entity_name": "[entity]",
#                 "attributes": ["[attribute]", ...]
#             }},
#             ...
#         ]
#     }}\n\n
#     Disregard any relations with unknown subjects or objects, and ensure that predicates strictly adhere to the provided list, replacing the text within hashtags as needed.\n\n
#     {task}
# """

# template = """
#     You are a relation extractor tasked with identifying entities and their relations from textual content. Your objective is to discern the key entities within a given text and ascertain the relations among them based on a predefined list of predicates. The entities could encompass a variety of concepts, including but not limited to individuals, organizations, locations (such as countries, states, cities, etc.), and dates, and other identifiable objects or concepts.\n\n
#     First, provide a short summary of the given text, focusing on all the possible relations and whether they would apply or not. When analyzing the text, focus on extracting entities that are explicitly mentioned and determine how they are interconnected through one-on-one relationships. Make sure to justify why this relation apply to these entities. It is crucial to use only the following list of predicates to define the relationships between entities: ['parent_of', 'spouse_of', 'member_of', 'employed_by', 'follow_religion', 'has_job', 'date_of_birth', 'date_of_death', 'part_of_#LOCATION_TYPE#', 'born_in_#LOCATION_TYPE#', 'died_in_#LOCATION_TYPE#', 'resides_in_#LOCATION_TYPE#']. #LOCATION_TYPE# needs to be replaced by the correct location type: country, state, city, etc. \n\nImportantly, when a date is mentioned in the text, treat it as an entity and establish a relationship with the relevant individual using the 'date_of_birth' or 'date_of_death' predicates. For example, if the text states that an individual died on a specific date in a specific location, extract and define the relations to include 'died_in_#LOCATION_TYPE#' with the location and 'date_of_death' with the specified date.\n\nYour results should be structured as a list of JSON objects, each representing a pair of entities and the relation between them, guided by the predicates from the list above. Additionally, identify the type of the entities mentioned in the text, using the following list: location, person, date, organisation or activity. Make sure the type adhere to the provided list, choosing the type that fits the entity the best (ex: a job would be an activity). Then, identify any attributes of those entities. An attribute could be any characteristic, quality, or identifiable feature of an entity as specified in the context. The format of your output should be as follows:\n
#     {{
#         "summary": "[short summary of the text]",
#         "relations": [
#             {{
#                 "subject": "[entity1]",
#                 "predicate": "[predicate from the list]",
#                 "object": "[entity2]"
#             }},
#             ...
#         ],
#         "entities": [
#             {{
#                 "entity_name": "[entity]",
#                 "type": "[type]",
#                 "attributes": ["[attribute]", ...]
#             }},
#             ...
#         ]
#     }}\n\n
#     Disregard any relations with unknown subjects or objects, and ensure that predicates strictly adhere to the provided list, replacing the text within hashtags as needed.
# """

template = """
    You are a relation extractor tasked with identifying entities and their relations from textual content. Your objective is to discern the key entities within a given text and ascertain the relations among them based on a predefined list of predicates. The entities could encompass a variety of concepts, including but not limited to individuals, organizations, locations (such as countries, states, municipality, cities, etc.), and dates, and other identifiable objects or concepts.\n\n
    First, provide a short summary of the given text, focusing on all the possible relations and whether they would apply or not. When analyzing the text, focus on extracting entities that are explicitly mentioned and determine how they are interconnected through one-on-one relationships. Make sure to justify why this relation apply to these entities. It is crucial to use only the following list of predicates to define the relationships between entities: ['parent_of', 'spouse_of', 'member_of', 'employed_by', 'follow_religion', 'has_job', 'date_of_birth', 'date_of_death', 'part_of_location', 'born_in_location', 'died_in_location', 'resides_in_location', likes_entertainement, dislikes_entertainement]. \n\nImportantly, when a date is mentioned in the text, treat it as an entity and establish a relationship with the relevant individual using the 'date_of_birth' or 'date_of_death' predicates. For example, if the text states that an individual died on a specific date in a specific location, extract and define the relations to include 'died_in_location' with the location and 'date_of_death' with the specified date.\n\nYour results should be structured as a list of JSON objects, each representing a pair of entities and the relation between them, guided by the predicates from the list above. Identify the type of the entities mentioned in the text, using the following list: location, person, date, organisation, activity, entertainement, etc. Additionally, identity the subtype of the entities mentioned in the text, using the following list: country, state, municipality, city, person, date, organisation, job, sport, movie, tv show, video games, etc. Make sure the type adhere to the provided list, choosing the type that fits the entity the best (ex: a job would be an activity). Then, identify any attributes of those entities. An attribute could be any characteristic, quality, or identifiable feature of an entity as specified in the context. The format of your output should be as follows:\n
    {{
        "summary": "[short summary of the text]",
        "relations": [
            {{
                "subject": "[entity1]",
                "predicate": "[predicate from the list]",
                "object": "[entity2]"
            }},
            ...
        ],
        "entities": [
            {{
                "entity_name": "[entity]",
                "type": "[type]",
                "subtype": "[subtype]",
                "attributes": ["[attribute]", ...]
            }},
            ...
        ]
    }}\n\n
    Disregard any relations with unknown subjects or objects, and ensure that predicates strictly adhere to the provided list.
"""

# currently_speaking = " The person who is currently talking in the text is called 'PersonA' and counts as an entity.\n\n"
# template += currently_speaking

template += "\n\n{task}"


prompt = ChatPromptTemplate.from_template(template)
model = ChatOpenAI()

#set_debug(True)

chain = (
    {"task": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)

input = "Billy Mays, the bearded, boisterous pitchman who, as the undisputed king of TV yell and sell, became an unlikely pop culture icon, died at his home in Tampa, Fla, on sunday march 23 2024. He was a devout christan and will be survived by his daughter Catherine."

# input = "Punta Cana is a resort town in the municipality of Higuey, in La Altagracia Province, the eastern most province of the Dominican Republic"

# input = "Senate majority leader Bill Frist likes to tell a story from his days as a pioneering heart surgeon back in Tennessee."

#input = "Oh, the weather's pretty neat here in Tennessee where I live."

# input = "Oh, I like the movie Blade Runner, it's one of my favorite movies."

question = f"Text: {input}" + "\n\nOutput:"

result = chain.invoke(question)

print(result)