from os import environ

SESSION_CONFIGS = [
    # dict(
    # name='rsd_prolific',
    # display_name="Matching by RSD on Prolific",
    # app_sequence=['rsd_prolific'],
    # num_demo_participants=1,
    # #use_browser_bots=True
    # ),
    dict(
        name='rsd_lab_t2',
        display_name = "Matching by RSD in the lab (treatment 2)",
        app_sequence=['rsd_lab_a_ne', 'rsd_lab_na_e'],
        num_demo_participants=4,
        participation_fee=5.00,
    ),
    dict(
        name = 'rsd_lab_t1',
        display_name = "Matching by RSD in the lab (treatment 1)",
        app_sequence = ['rsd_lab_a_e', 'rsd_lab_na_ne'],
        num_demo_participants = 4,
        participation_fee = 5.00,
    ),
    dict(
        name='rsd_lab_live',
        display_name="Sequential RSD (live)",
        app_sequence=['rsd_lab_live_a', 'rsd_lab_live_na'],
        num_demo_participants=4,
        participation_fee=5.00,
    )
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=1.00, doc=""
)

PARTICIPANT_FIELDS = [
    'e1_schedule',
    'e1_successful',
    'e1_valuations',
    'e1_player_prefs',
    'e1_selected_pay_round',
    'e1_app_payoff',
    'e2_schedule',
    'e2_successful',
    'e2_valuations',
    'e2_player_prefs',
    'e2_selected_pay_round',
    'e2_app_payoff',
    'e3_schedule',
    'e3_successful',
    'e3_valuations',
    'e3_player_prefs',
    'e3_selected_pay_round',
    'e3_app_payoff',
    'total_payment',
]
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '5600746447951'
