import streamlit as st
import time
import os
import backend
import frontend
import config
import llm
import pages
from supa_adapter import SupabaseAdapter

# Init interface
frontend.initUI()
backend.init_sessions()

# Supabase client
supabaseObj = SupabaseAdapter()
 
# Menu: choose page
chosen_page = pages.display_menu()

# Page redirection
pages.page_redirection(chosen_page, supabaseObj)



