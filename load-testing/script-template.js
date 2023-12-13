import http from 'k6/http';

const testing_stages = [
  { target: 100, duration: '15m' }, // 00:15
  { target: 40, duration: '15m' }, // 00:30
  { target: 90, duration: '15m' }, // 00:45
  { target: 50, duration: '15m' }, // 01:00
  { target: 110, duration: '15m' }, // 01:15
  { target: 40, duration: '15m' }, // 01:30
  { target: 700, duration: '10m' }, // 01:40
  { target: 50, duration: '10m' }, // 01:50
  { target: 500, duration: '130m' }, // 04:00
  { target: 15, duration: '5m' }, // 04:05
  { target: 500, duration: '10m' }, // 04:15
  { target: 500, duration: '25m' }, // 04:40
  { target: 15, duration: '80m' }, // 06:00
]

export const options = {
  tags: {
    execution_id: 'EXECUTION_ID',
  },
  discardResponseBodies: true,
  scenarios: {
    ec2: {
      executor: 'ramping-arrival-rate',
      exec: 'ec2',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 1000,
      stages: testing_stages,
    },
    ecs: {
      executor: 'ramping-arrival-rate',
      exec: 'ecs',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 1000,
      stages: testing_stages,
    },
    lambda: {
      executor: 'ramping-arrival-rate',
      exec: 'lambda',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 1000,
      stages: testing_stages,
    },
  },
};
  
export function ec2() {
  http.get('EC2_API_URL');
}

export function ecs() {
  http.get('ECS_API_URL');
}

export function lambda() {
  http.get('LAMBDA_API_URL');
}