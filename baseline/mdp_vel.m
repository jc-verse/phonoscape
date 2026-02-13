function data = mdp_vel(data, varargin)
%MDP_VEL  - MVIEW dataproc that appends separately scaled velocities for specified trajectories
%
%	varargin{1} - cellstr list of trajectories, followed by optional common scaling factor and
%	                low-pass Fc (default none)
%
% Because this takes arguments (the cellstr array of trajectories) it must be embedded as
% a cell element within the DPROC list (i.e., nested within {})
%
% returns tangential velocity unless input signal is monodimensional (components > 3 ignored)
%
% usage example:  mview(...,'DPROC',{{'mdp_vel',{'HEAD1','HEAD2'}}}, ...)
% clip to 3 cm/s: mview(...,'DPROC',{{'mdp_vel',{'HEAD1','HEAD2',3}}}, ...)
% clip to 3 cm/s after LP filtering @5Hz: mview(...,'DPROC',{{'mdp_vel',{'HEAD1','HEAD2',[3 5]}}}, ...)

% mkt 11/13

names = upper({data.NAME});
traj = varargin(1:end-1);		% last arg is {pal,phar,labs}
filt = [];
if ischar(traj{end}),
	scale = [];
else,
	scale = traj{end};
	if length(scale) > 1,
		filt = scale(2);
		scale = scale(1);
	end;
	traj(end) = [];
end;
for ti = 1 : length(traj),
	k = strmatch(traj{ti},names,'exact');
	if isempty(k),
		error('%s not found in dataset', traj{ti});
	end;
	data(end+1) = data(k);
	data(end).NAME = [traj{ti},'_vel'];
	if size(data(end).SIGNAL,2) > 1, ds = data(end).SIGNAL(:,1:3); else, ds = data(end).SIGNAL; end
	if ~isempty(filt),
		sr = data(end).SRATE;
		[b,a] = butter(3,filt*2/sr,'low');
		fq = NaN(size(ds));
		bad = find(isnan(ds));
		good = find(all(~isnan(ds),2));
		if isempty(good), 					% all bad -- give up
			error('missing data in all %d frames of %s', size(ds,1), traj{ti});
		end;
		if isempty(bad),
			qq = ds;						% none are missing
		else,								% interpolate across missing data points for LP filtering
			qq = interp1(good,ds(good,:),linspace(good(1),good(end),good(end)-good(1)+1)','pchip');
			fprintf('missing data in %d / %d frames of %s', sum(any(isnan(ds),2)), size(ds,1), traj{ti});
		end;
		fq(good(1):good(end),:) = filtfilt(b,a,qq);
		fq(bad) = NaN;						% restore missing status
		ds = fq;
	end;
	ds = data(end).SRATE * [diff(ds([1 3],:)) ; ds(3:end,:) - ds(1:end-2,:) ; diff(ds([end-2 end],:))] ./ 20;	% cm/sec
	if size(ds,2) > 1,						% compute tangential velocity
		nc = max([3,size(ds,2)]);			% ignore angular components
		data(end).SIGNAL = sqrt(sum(ds(:,1:nc).^2,2)); 
	else,
		data(end).SIGNAL = ds;
	end;
	if ~isempty(scale),
		data(end).SIGNAL(data(end).SIGNAL > scale) = NaN;
	end;
	minS = min(data(end).SIGNAL);
	maxS = max(data(end).SIGNAL);
	spread = maxS - minS;
	data(end).SPREAD = [minS-spread*.1 maxS+spread*.1];		% pad
	data(end).NCOMPS = 1;
end;
