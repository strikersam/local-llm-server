import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import TasksPage from '../pages/TasksPage';

jest.mock('../api', () => ({
  addTaskComment: jest.fn(),
  createTask: jest.fn(),
  escalateTask: jest.fn(),
  fmtErr: (value) => value?.message || String(value),
  listAgents: jest.fn(),
  listRuntimes: jest.fn(),
  listTasks: jest.fn(),
  retryTask: jest.fn(),
  runTask: jest.fn(),
  updateTask: jest.fn(),
}));

const {
  createTask,
  listAgents,
  listRuntimes,
  listTasks,
  runTask,
} = require('../api');

beforeEach(() => {
  jest.clearAllMocks();
  listTasks.mockResolvedValue({ data: { tasks: [] } });
  listAgents.mockResolvedValue({
    data: {
      agents: [
        { agent_id: 'agent_writer', name: 'Writer' },
      ],
    },
  });
  listRuntimes.mockResolvedValue({
    data: {
      runtimes: [
        { runtime_id: 'internal_agent', display_name: 'Internal Agent' },
      ],
    },
  });
  runTask.mockResolvedValue({ data: { queued: true } });
});

test('create and run uses the selected agent/runtime and triggers immediate execution', async () => {
  createTask.mockResolvedValueOnce({
    data: {
      task: {
        task_id: 'task_123',
        title: 'Fix task flakiness',
        status: 'in_progress',
      },
    },
  });

  render(<TasksPage />);

  const user = userEvent.setup();
  await screen.findByRole('heading', { name: 'Tasks' });
  await user.click(screen.getByRole('button', { name: /new task/i }));
  await user.type(screen.getByTestId('task-form-title'), 'Fix task flakiness');
  await user.type(screen.getByTestId('task-form-prompt'), 'Re-run the failing task with the internal runtime.');
  await user.selectOptions(screen.getByTestId('task-form-agent'), 'agent_writer');
  await user.selectOptions(screen.getByTestId('task-form-runtime'), 'internal_agent');
  await user.selectOptions(screen.getByTestId('task-form-type'), 'code_generation');
  await user.click(screen.getByRole('button', { name: /create & run/i }));

  await waitFor(() => expect(createTask).toHaveBeenCalledTimes(1));
  expect(createTask).toHaveBeenCalledWith(expect.objectContaining({
    title: 'Fix task flakiness',
    prompt: 'Re-run the failing task with the internal runtime.',
    agent_id: 'agent_writer',
    runtime_id: 'internal_agent',
    task_type: 'code_generation',
    status: 'in_progress',
  }));
  await waitFor(() => expect(runTask).toHaveBeenCalledWith('task_123'));
});

test('run now action is available from the task detail panel', async () => {
  listTasks.mockResolvedValue({
    data: {
      tasks: [
        {
          task_id: 'task_run_now',
          title: 'Run this task',
          status: 'todo',
          priority: 'medium',
          updated_at: Math.floor(Date.now() / 1000),
          comments: [],
          execution_log: [],
        },
      ],
    },
  });

  render(<TasksPage />);

  const user = userEvent.setup();
  await screen.findByText('Run this task');
  await user.click(screen.getByText('Run this task'));
  await user.click(screen.getByRole('button', { name: /run now/i }));

  await waitFor(() => expect(runTask).toHaveBeenCalledWith('task_run_now'));
});
