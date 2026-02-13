function data = mdp_AZEL(data, varargin)
%MDP_AZEL  - MVIEW dataproc that computes azimuth and elevation from dual-EMA head refs
%
% assumes that trajectories HUI1|2, HLR1|2, HRR1|2 available
%
% appends HAZ1|2, HEL1|2
%
% AZ is offset such that straight ahead is 0 for each speaker, -right, +left
% EL tilted down negative, both in degrees

% mkt 05/15

tn = {'HUI','HLR','HRR'};
names = upper({data.NAME});
for si = 1 : 2,
	for ti = 1 : 3,
		idx(ti) = find(strcmp(sprintf('%s%d',tn{ti},si), names));
	end
	d = NaN(size(data(idx(1)).SIGNAL,1),3,3);
	for ti = 1 : 3, d(:,:,ti) = data(idx(ti)).SIGNAL(:,1:3); end
	d = d - repmat(nanmean(nanmean(d,3)),[size(d,1),1,3]);		% center on centroid
	n = cross(d(:,:,1) - d(:,:,2) , d(:,:,1) - d(:,:,3) , 2);	% compute normal to plane
	a = acos(n ./ (sqrt(nansum(n.^2,2))*ones(1,3)));			% direction cosines
	az = atan2(cos(a(:,1)),cos(a(:,2)));
	if si == 1, 
		az = az - pi/2;				% face each other
	else,
		az = az + pi/2;
	end
	el = -a(:,3);					% head tilted down is negative

	data(end+1) = data(idx(1));
	data(end).NAME = sprintf('HAZ%d',si);
	data(end).SIGNAL = az*180/pi;
	minS = min(data(end).SIGNAL);
	maxS = max(data(end).SIGNAL);
	spread = maxS - minS;
	data(end).SPREAD = [minS-spread*.1 maxS+spread*.1];		% pad
	data(end).NCOMPS = 1;

	data(end+1) = data(idx(2));
	data(end).NAME = sprintf('HEL%d',si);
	data(end).SIGNAL = el*180/pi;
	minS = min(data(end).SIGNAL);
	maxS = max(data(end).SIGNAL);
	spread = maxS - minS;
	data(end).SPREAD = [minS-spread*.1 maxS+spread*.1];		% pad
	data(end).NCOMPS = 1;
end
