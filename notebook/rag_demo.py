from notebook.tools_demo import agent

query = input("Enter")
result = agent.run_sync(query)
print(result.output)
print(list(agent._function_toolset.tools))
