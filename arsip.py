 # # User Input
    # user_prompt = st.text_input("Ask a question about your data and get a visualization:")
    
    # if st.button("Generate Visualization"):
    #     with st.spinner("Generating Intelligent Visualization..."):
    #         try:
    #             # LLM Configuration
    #             llm = ChatOllama(model="llama3.2-vision")
                
    #             # Create processing chain
    #             chain = prompt | llm | StrOutputParser()
    #             viz_instruction_str = chain.invoke({
    #                 'columns': ', '.join(df.columns), 
    #                 'question': user_prompt,
    #             })
                
    #             # In your main function, before parsing
    #             print("Raw LLM Response:", viz_instruction_str)
                
    #             try:
    #                 viz_instruction = parse_visualization_instruction(viz_instruction_str)
                    
    #                 if viz_instruction is None:
    #                     fallback_visualization(df, user_prompt)
    #                     return
                
    #                 # Cetak instruksi untuk debugging
    #                 st.write("Visualization Instruction:", viz_instruction)
                    
    #                 # Proses visualisasi
    #                 chart_type = viz_instruction.get('chart_type', 'bar')
                    
    #                 if chart_type in ['bar', 'scatter', 'line', 'pie']:
    #                     # Sesuaikan mapping nama chart
    #                     plotly_type = {
    #                         'bar': 'bar_chart',
    #                         'scatter': 'scatter_plot',
    #                         'line': 'line_chart',
    #                         'pie': 'pie_chart'
    #                     }.get(chart_type, 'bar_chart')
                        
    #                     # Buat objek sederhana untuk visualisasi
    #                     viz_obj = type('VizObj', (), {
    #                         'visualization_type': plotly_type,
    #                         'x_column': viz_instruction.get('x_column', df.columns[0]),
    #                         'y_column': viz_instruction.get('y_column', df.columns[1] if len(df.columns) > 1 else df.columns[0]),
    #                         'title': viz_instruction.get('title', 'Data Visualization'),
    #                         'additional_instructions': viz_instruction.get('additional_instructions', {})
    #                     })
                        
    #                     fig = create_dynamic_visualization(df, viz_obj)
    #                     st.plotly_chart(fig, use_container_width=True)
                    
    #                 elif chart_type == 'map':
    #                     map_chart = create_map_visualization(df, viz_instruction)
    #                     if map_chart:
    #                         st.pydeck_chart(map_chart)
    #                     else:
    #                         fallback_visualization(df, user_prompt)
                    
    #                 else:
    #                     fallback_visualization(df, user_prompt)
                
    #             except Exception as e:
    #                 st.warning(f"Gagal membuat visualisasi AI: {e}")
    #                 fallback_visualization(df, user_prompt)
            
    #         except Exception as e:
    #             st.error(f"Error umum: {e}")
    #             fallback_visualization(df, user_prompt)